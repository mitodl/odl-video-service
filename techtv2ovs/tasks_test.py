""" Tests for techtv2ovs tasks """
import pytest

from odl_video.settings import VIDEO_S3_TRANSCODE_BUCKET, VIDEO_S3_BUCKET
from techtv2ovs.constants import TTV_VIDEO_BUCKET, ImportStatus
from techtv2ovs.factories import TechTVVideoFactory
from techtv2ovs.models import TechTVVideo
from techtv2ovs.tasks import process_videofiles, parse_encoding
from ui.constants import VideoStatus
from ui.models import VideoFile

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('s3_copy', [True, False])
@pytest.mark.parametrize('s3_files', [
    [],
    [
        {'Bucket': TTV_VIDEO_BUCKET, 'Key': 'Key0/original.m4v'},
        {'Bucket': TTV_VIDEO_BUCKET, 'Key': 'Key1/small.mp4'},
        {'Bucket': TTV_VIDEO_BUCKET, 'Key': 'Key2/hd.mp4'},
        {'Bucket': TTV_VIDEO_BUCKET, 'Key': 'Key3/medium.mp4'},
    ]
])
def test_process_videofiles(mocker, s3_copy, s3_files):
    """
    Test that videofiles are created for each s3 file if any, and statuses updated appropriately
    """
    mock_boto = mocker.patch('techtv2ovs.tasks.boto3')
    mock_s3_objects = mock_boto.client('s3').list_objects_v2
    mock_s3_objects.return_value = s3_files
    ttv = TechTVVideoFactory()
    process_videofiles.apply(args=[ttv.id, s3_files, s3_copy])
    processed_ttv = TechTVVideo.objects.get(id=ttv.id)
    assert len(processed_ttv.video.videofile_set.all()) == len(s3_files)
    for file in s3_files:
        assert len(VideoFile.objects.filter(
            video=processed_ttv.video,
            bucket_name=(VIDEO_S3_BUCKET if 'original' in file['Key'] else VIDEO_S3_TRANSCODE_BUCKET),
            encoding=parse_encoding(file['Key']),
            s3_object_key='{}techtv/{}'.format(
                '' if 'original' in file['Key'] else 'transcoded/',
                file['Key']
            )
        )) == 1
    assert mock_s3_objects.call_count == (len(s3_files) if s3_copy else 0)
    assert processed_ttv.videofile_status == (ImportStatus.COMPLETE if s3_files else ImportStatus.MISSING)
    assert processed_ttv.status == processed_ttv.videofile_status
    assert processed_ttv.video.status == (VideoStatus.ERROR if not s3_files else VideoStatus.COMPLETE)


def test_process_videofiles_error(mocker):
    """
    Test that statuses are updated appropriately to ERROR if anything goes wrong
    """
    mock_boto = mocker.patch('techtv2ovs.tasks.boto3')
    mock_s3_objects = mock_boto.client('s3').list_objects_v2
    mock_s3_objects.side_effect = OSError
    s3_files = [{'Bucket': TTV_VIDEO_BUCKET, 'Key': 'Key1/small.mp4'}]
    ttv = TechTVVideoFactory()
    process_videofiles.apply(args=[ttv.id, s3_files, True])
    processed_ttv = TechTVVideo.objects.get(id=ttv.id)
    assert list(processed_ttv.video.videofile_set.all()) == []
    assert processed_ttv.videofile_status == ImportStatus.ERROR
    assert processed_ttv.status == ImportStatus.ERROR
    assert processed_ttv.video.status == VideoStatus.ERROR


@pytest.mark.parametrize(['file', 'expected'], [
    ['sdfksdieurekdjf/original.m4v', 'original'],
    ['1/2/3/4/basic.mp4', 'basic'],
    ['large.mp4', 'large'],
    ['a/b/hd.mp4', 'HD']
])
def test_parse_encoding(file, expected):
    """ Test that correct encodings are assigned based on file names """
    assert parse_encoding(file) == expected
