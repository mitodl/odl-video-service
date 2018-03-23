""" Test model signals"""
import pytest
from django.test import override_settings

from ui.constants import StreamSource, YouTubeStatus
from ui.encodings import EncodingNames
from ui.factories import VideoFactory, YouTubeVideoFactory, VideoSubtitleFactory, VideoFileFactory
from ui.models import YouTubeVideo

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name,too-many-arguments


@pytest.fixture()
def video_with_file():
    """ Fixture to create a video with an original videofile """
    video = VideoFactory(is_public=True)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)
    return video


@pytest.mark.parametrize("enable_video_permissions", [True, False])
def test_youtube_video_delete_signal(mocker, settings, enable_video_permissions):
    """ Tests that a video's YouTubeVideo object is deleted after changing from public to private"""
    settings.ENABLE_VIDEO_PERMISSIONS = enable_video_permissions
    mock_task = mocker.patch('ui.signals.remove_youtube_video.delay')
    video = VideoFactory(is_public=True)
    yt_video = YouTubeVideoFactory(video=video)
    assert YouTubeVideo.objects.filter(id=yt_video.id).first() == yt_video
    video.is_public = False
    video.save()
    expected_call_count = 1 if enable_video_permissions else 0
    assert mock_task.call_count == expected_call_count


@pytest.mark.parametrize("enable_video_permissions", [True, False])
def test_youtube_video_permissions_signal(mocker, settings, enable_video_permissions):
    """ Tests that a video's public permissions are removed if it's subtitle is deleted """
    settings.ENABLE_VIDEO_PERMISSIONS = enable_video_permissions
    mock_delete_video = mocker.patch('ui.signals.remove_youtube_video.delay')
    mock_delete_caption = mocker.patch('ui.signals.remove_youtube_caption.delay')
    mocker.patch('ui.models.VideoSubtitle.delete_from_s3')
    video = VideoFactory(is_public=enable_video_permissions)
    YouTubeVideoFactory(video=video)
    VideoSubtitleFactory(video=video)
    VideoSubtitleFactory(video=video, language='fr')
    video.videosubtitle_set.get(language='fr').delete()
    # video's public status should not be changed as long as 1 subtitle still exists
    assert video.is_public == enable_video_permissions
    expected_call_count = 1 if enable_video_permissions else 0
    assert mock_delete_caption.call_count == expected_call_count
    video.videosubtitle_set.first().delete()
    # If no subtitles exists, video should be made non-public and deleted from youtube
    assert mock_delete_video.call_count == expected_call_count
    assert not video.is_public
    caption = VideoSubtitleFactory(video=video)
    mock_video_save = mocker.patch('ui.models.Video.save')
    caption.delete()
    # If video is not public, no change to it should be saved after a caption is deleted.
    assert mock_video_save.call_count == 0


@pytest.mark.parametrize(["is_public", "on_youtube", "delete_count"], [
    [True, True, 0],
    [True, False, 0],
    [False, True, 1],
    [False, False, 0]
])
@override_settings(ENABLE_VIDEO_PERMISSIONS=True)
def test_youtube_sync_signal(mocker, is_public, on_youtube, delete_count, video_with_file):
    """Tests tasks for deleting from YouTube are called when appropriate."""
    mock_delete = mocker.patch('ui.signals.YouTubeVideo.delete')
    if on_youtube:
        YouTubeVideoFactory(video=video_with_file)
    collection = video_with_file.collection
    collection.stream_source = StreamSource.CLOUDFRONT
    collection.save()
    assert mock_delete.call_count == (1 if is_public and on_youtube else delete_count)


@pytest.mark.parametrize('status', [YouTubeStatus.REJECTED, YouTubeStatus.FAILED, YouTubeStatus.UPLOADED])
@override_settings(ENABLE_VIDEO_PERMISSIONS=True)
def test_youtube_sync_redo_failed(mocker, video_with_file, status):
    """ Test that an existing youtube video is deleted if it has a bad status"""
    mock_delete = mocker.patch('ui.signals.YouTubeVideo.delete')
    YouTubeVideoFactory(video=video_with_file, status=status)
    video_with_file.is_public = True
    video_with_file.save()
    expected_count = (0 if status == YouTubeStatus.UPLOADED else 1)
    assert mock_delete.call_count == expected_count
