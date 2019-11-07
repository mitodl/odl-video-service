"""
ui model signals
"""
# pylint: disable=unused-argument
from django.conf import settings
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out

from cloudsync.tasks import remove_youtube_video, remove_youtube_caption
from ui.constants import StreamSource, YouTubeStatus
from ui.models import VideoFile, VideoThumbnail, VideoSubtitle, Video, YouTubeVideo, Collection
from ui import tasks as ovs_tasks
from ui.utils import delete_moira_cache, edx_settings_configured


@receiver(pre_delete, sender=VideoFile)
@receiver(pre_delete, sender=VideoThumbnail)
@receiver(pre_delete, sender=VideoSubtitle)
def delete_s3_files(sender, **kwargs):
    """
    Make sure S3 files are deleted along with associated video file/thumbnail object
    """
    kwargs['instance'].delete_from_s3()


@receiver(pre_delete, sender=VideoSubtitle)
def update_video_permissions(sender, **kwargs):
    """
    Remove public video permissions if the subtitle is about to be deleted and no other subtitles exist.
    Otherwise just delete the subtitle from Youtube.
    """
    video = kwargs['instance'].video
    if video.is_public:
        if video.techtvvideo_set.first() is None and len(video.videosubtitle_set.all()) <= 1:
            video.is_public = False
            video.save()
        elif YouTubeVideo.objects.filter(video=video).first() is not None:
            remove_youtube_caption.delay(video.id, kwargs['instance'].language)


@receiver(pre_delete, sender=YouTubeVideo)
def delete_youtube_video(sender, **kwargs):
    """
    Call the YouTube API to delete a video
    """
    youtube_id = kwargs['instance'].id
    if youtube_id is not None:
        remove_youtube_video.delay(youtube_id)


@receiver(post_save, sender=Collection)
def update_collection_youtube(sender, **kwargs):
    """
    If a collection's stream source is changed, sync YoutubeVideo objects for public Videos
    """
    for video in kwargs['instance'].videos.filter(is_public=True):
        sync_youtube(video)


@receiver(post_save, sender=Collection)
def update_collection_retranscodes(sender, **kwargs):
    """
    Sync schedule_retranscode value for all videos in the collection
    """
    if settings.FEATURES.get("RETRANSCODE_ENABLED", False):
        collection = kwargs['instance']
        Video.objects.filter(collection=collection).update(schedule_retranscode=collection.schedule_retranscode)


@receiver(post_save, sender=Video)
def update_video_youtube(sender, **kwargs):
    """
    If a video's is_public field is changed, sync associated YoutubeVideo object
    """
    sync_youtube(kwargs['instance'])


@receiver(post_save, sender=VideoFile)
def add_hls_to_edx(sender, instance, created, **kwargs):
    """
    If an HLS VideoFile was created and the correct edX settings are present, kick off a task
    to add this video to edX via API.
    """
    if created and edx_settings_configured() and instance.can_add_to_edx():
        ovs_tasks.post_hls_to_edx.delay(instance.id)


def sync_youtube(video):
    """
    Delete from youtube if it exists and permissions are not public or collection stream_source == cloudfront.

    Args:
        video(ui.models.Video): The video that should be uploaded or deleted from Youtube.
    """
    yt_video = video.youtubevideo if hasattr(video, 'youtubevideo') else None
    if yt_video is not None:
        if (video.is_public is False or video.collection.stream_source == StreamSource.CLOUDFRONT or
                yt_video.status in (YouTubeStatus.FAILED, YouTubeStatus.REJECTED)):
            YouTubeVideo.objects.get(id=yt_video.id).delete()


def reset_moira(sender, user, request, **kwargs):
    """
    Clear out the user's cached moira lists

    Args:
        sender(Object): The sender of the signal
        user(User): The user logging out
        request(WSGIRequest): The request to log out
    """
    delete_moira_cache(user)


user_logged_out.connect(reset_moira)
