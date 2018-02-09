""" Tests for techtv2ovs.utils """
import pytest
from bonobo.structs import Graph

from techtv2ovs.constants import ImportStatus
from techtv2ovs.factories import TechTVCollectionFactory, TechTVVideoFactory
from techtv2ovs.models import TechTVCollection, TechTVVideo
from techtv2ovs.utils import moiralist_name, get_owner, remove_tags, TechTVImporter, get_s3_videos
from ui.constants import VideoStatus
from ui.factories import UserFactory
from ui.models import VideoThumbnail

# pylint: disable=redefined-outer-name

pytestmark = pytest.mark.django_db


@pytest.fixture
def importer():
    """ Fixture to create a TechTVImporter """
    ttv_importer = TechTVImporter()
    ttv_importer.connection = None
    return ttv_importer


@pytest.mark.parametrize(['cid', 'name', 'moiralist'], [
    [2137, '"It\'s Not My Cause"', 'techtv-2137-it-s-not-my-cause'],
    [1111, '"What is Engineering?"', 'techtv-1111-what-is-engineering'],
    [2121, '$100,000 Lemelson-MIT Award for Global Innovation', 'techtv-2121-100-000-lemelson-mit-award-for-g'],
    [
        33,
        '10th Anniversary of the Pappalardo Fellowships in Physics Symposium',
        'techtv-33-10th-anniversary-of-the-pappalar'
    ],
    [4, '14.73: The Challenges of Global Poverty', 'techtv-4-14-73-the-challenges-of-global-p'],
    [9, '5974B - 12 May', 'techtv-9-5974b-12-may'],
    [123, '2.003J/1.053J Dynamics and Control 1 -- Fall 2010', 'techtv-123-2-003j-1-053j-dynamics-and-contr'],
    [1, 'Behind the Scenes at MIT; http://chemvideos.mit.edu', 'techtv-1-behind-the-scenes-at-mit-http-ch'],
    [5555, '[21W.752/21W.824] Video Editing Assignment', 'techtv-5555-21w-752-21w-824-video-editing-as'],
    [3, 'avivas@mit.edu\'s collection', 'techtv-3-avivas-mit-edu-s-collection'],
    [99, 'Center for Graphene Devices & 2D Systems', 'techtv-99-center-for-graphene-devices-2d-s']
])
def test_moiralist_name(cid, name, moiralist):
    """ Test that expected moira list names are returned """
    assert moiralist_name(cid, name) == moiralist


@pytest.mark.parametrize(['email', 'owner'], [
    ['user1@mit.edu', 'user1@mit.edu'],
    ['user2@gmail.com', 'admin']
])
def test_get_owner(settings, email, owner):
    """ Test that expected owner is returned for an email address """
    settings.LECTURE_CAPTURE_USER = 'admin'
    UserFactory(username='admin')
    assert get_owner(email).username == owner


@pytest.mark.parametrize(['html', 'text'], [
    ['<p>This is <a href="http://foo.com">a link</a></p>', 'This is a link'],
    ['10 > 7 < 12', '10 > 7 < 12'],
    ['7 < 12 > 10', '7 < 12 > 10'],
    ['The cat ate the &nbsp; rat', 'The cat ate the   rat'],
    ['2 + 3 &gt; 4', '2 + 3 > 4'],
    ['The link is http://mit.edu', 'The link is http://mit.edu'],
    [None, '']
])
def test_remove_tags(html, text):
    """ Test that HTML tags are removed from strings """
    assert remove_tags(html) == text


@pytest.mark.parametrize('collection', [None, 123])
def test_extract_collections(mocker, importer, collection):
    """ Assert that TechTVImporter.extract_collections returns MySQL query results  """
    importer.collection = collection
    collection_data = (('123', 'My Collection', 'My Description', 'foo@mit.edu'),)
    mocker.patch('techtv2ovs.utils.mysql_query', return_value=collection_data)
    assert list(importer.extract_collections()) == list(collection_data)


def test_process_collection(mocker, importer):
    """ Assert that correct collection objects are created by TechTVImporter.process_collection """
    mocker.patch('techtv2ovs.utils.TechTVImporter.process_videos')
    collection_data = ('123', 'My Collection', 'My Description', 'foo@mit.edu')
    importer.process_collection(*collection_data)
    ttvcollection = TechTVCollection.objects.get(id=collection_data[0])
    assert ttvcollection.name == collection_data[1]
    assert ttvcollection.collection.title == collection_data[1]
    assert ttvcollection.description == collection_data[2]
    assert ttvcollection.collection.description == collection_data[2]
    assert list(
        ttvcollection.collection.view_lists.values_list('name', flat=True)
    ) == ['techtv-123-my-collection']
    assert list(
        ttvcollection.collection.admin_lists.values_list('name', flat=True)
    ) == ['techtv-123-my-collection-owner']


@pytest.mark.parametrize('s3files', [
    [],
    [{'Bucket': 'techtv', 'Key': 'testing123/hd.mp4'}]
])
def test_process_videos(mocker, s3files, importer):
    """ Assert that correct video objects are created by TechTVImporter.process_videos"""
    ttvcollection = TechTVCollectionFactory()
    video_data = (('456', 'My Video', 'My Description', '123asda23', 0, None),)
    s3_videos = mocker.patch('techtv2ovs.utils.get_s3_videos', return_value=s3files)
    mocker.patch('techtv2ovs.utils.mysql_query', return_value=video_data)
    mocker.patch('techtv2ovs.utils.TechTVImporter.process_files')
    importer.process_videos(ttvcollection)
    ttv_video = TechTVVideo.objects.get(ttv_collection=ttvcollection)
    assert ttv_video.title == video_data[0][1]
    assert ttv_video.description == video_data[0][2]
    assert ttv_video.status == (ImportStatus.CREATED if s3files else ImportStatus.MISSING)
    if s3files:
        assert ttv_video.video.status == VideoStatus.CREATED
        assert ttv_video.video.title == video_data[0][1]
        assert ttv_video.video.description == video_data[0][2]
    else:
        assert ttv_video.video is None
    assert s3_videos.call_count == 1


@pytest.mark.parametrize('aws', [True, False])
@pytest.mark.parametrize('s3files', [
    [],
    [{'Bucket': 'testBucket', 'Key': 'thumbnails/jumbo.jpg'}]
])
def test_process_thumbnails(mocker, settings, importer, s3files, aws):
    """ Test that VideoThumbnail objects are generated """
    settings.VIDEO_S3_THUMBNAIL_BUCKET = 'odl-video-service-thumbnails'
    importer.aws = aws
    ttv_video = TechTVVideoFactory()
    mock_boto = mocker.patch('techtv2ovs.utils.boto3')
    mock_s3_objects = mock_boto.client('s3').list_objects_v2
    mock_copy = mock_boto.client('s3').copy
    mock_s3_objects.return_value = {'Contents': s3files}
    importer.process_thumbs(ttv_video)
    if s3files:
        thumbnail = VideoThumbnail.objects.get(video=ttv_video.video)
        assert thumbnail.s3_object_key == 'thumbnails/techtv/{}/0.jpg'.format(ttv_video.video.hexkey)
        assert thumbnail.bucket_name == settings.VIDEO_S3_THUMBNAIL_BUCKET
    assert ttv_video.thumbnail_status == (ImportStatus.COMPLETE if s3files else ImportStatus.MISSING)
    assert mock_copy.call_count == (1 if aws and s3files else 0)


def test_process_thumbnails_error(mocker, settings, importer):
    """ Test that TTVVideo thumbnail statuses are correclty set on error """
    settings.VIDEO_S3_THUMBNAIL_BUCKET = 'odl-video-service-thumbnails'
    ttv_video = TechTVVideoFactory()
    importer.aws = True
    mock_boto = mocker.patch('techtv2ovs.utils.boto3')
    mock_s3_objects = mock_boto.client('s3').list_objects_v2
    mock_s3_objects.return_value = {'Contents': [{'Bucket': 'testBucket', 'Key': 'thumbnails/jumbo.jpg'}]}
    mock_boto.client('s3').copy.side_effect = OSError
    importer.process_thumbs(ttv_video)
    assert VideoThumbnail.objects.filter(video=ttv_video.video).first() is None
    assert ttv_video.thumbnail_status == ImportStatus.ERROR


@pytest.mark.parametrize('contents', [
    [{'Key': 'foo', 'Bucket': 'bar'}],
    []
])
def test_get_s3_videos(mocker, contents):
    """ Test that get_s3_videos returns expected contents """
    mock_boto = mocker.patch('techtv2ovs.utils.boto3')
    mock_s3_objects = mock_boto.client('s3').list_objects_v2
    mock_s3_objects.return_value = {'Contents': contents}
    assert get_s3_videos('foo') == contents


def test_process_files(mocker, importer):
    """ Test that process_files calls self.process_thumbs and tasks.process_videofiles """
    mock_process_thumbs = mocker.patch('techtv2ovs.utils.TechTVImporter.process_thumbs')
    mock_process_videofiles = mocker.patch('techtv2ovs.tasks.process_videofiles.delay')
    ttv_video = TechTVVideoFactory()
    importer.process_files(ttv_video, [])
    mock_process_thumbs.assert_called_once_with(ttv_video)
    mock_process_videofiles.assert_called_once_with(ttv_video.id, [], importer.aws)


def test_run(mocker, importer):
    """ Test that etl_graph is called by run method """
    mocker.patch('MySQLdb.connect')
    mock_graph = mocker.patch('techtv2ovs.utils.TechTVImporter.etl_graph')
    importer.run()
    mock_graph.assert_called_once()


def test_etl_graph(importer):
    """ Test that a graph is returned by etl_graph() """
    assert isinstance(importer.etl_graph(), Graph)
