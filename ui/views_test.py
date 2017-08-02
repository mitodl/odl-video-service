"""
Tests for views
"""
import json

from django.conf import settings
from django.test.utils import override_settings
from rest_framework.reverse import reverse


def test_index_anonymous(client):
    """Test index anonymous"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'login_form' in response.context_data
    assert 'register_form' in response.context_data
    assert response.template_name == ['ui/index.html']


def test_upload_anonymous(client):
    """Test upload anonymous"""
    response = client.get('/upload/')
    assert response.status_code == 302
    assert response['Location'] == '/login/?next=/upload/'


def test_upload(client, user):
    """Test upload"""
    client.force_login(user)
    response = client.get('/upload/')
    assert response.status_code == 302
    assert response['Location'] == '/login/?next=/upload/'


@override_settings(DROPBOX_KEY='dbkey')
def test_dropbox_keys_in_context(admin_client):
    """Test dropbox keys in context"""
    response = admin_client.get('/upload/')
    assert response.status_code == 200
    assert response.context_data['dropbox_key'] == 'dbkey'
    assert response.template_name == ['ui/upload.html']


def test_video_detail_hls(admin_client, video, videofileHLS, mocker):  # pylint: disable=unused-argument
    """Test video detail page when HLS videofile is available"""
    mocker.patch('ui.utils.get_cloudfront_signed_url', return_value=videofileHLS.cloudfront_url)
    video.status = 'Complete'
    url = reverse('video-detail', kwargs={'pk': video.id})
    response = admin_client.get(url)
    assert 'videofile' in response.context_data
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        'videofile': response.context_data['videofile'].cloudfront_url,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": '/static/bundles/'
    }


def test_video_detail_unencoded(
        admin_client, video_unencoded, videofile_unencoded, mocker):  # pylint: disable=unused-argument
    """Test video detail page when HLS videofile is not available"""
    mocker.patch('ui.utils.get_cloudfront_signed_url', return_value=videofile_unencoded.cloudfront_url)
    url = reverse('video-detail', kwargs={'pk': video_unencoded.id})
    video_unencoded.status = 'Complete'
    response = admin_client.get(url)
    assert 'videofile' in response.context_data
    assert response.context_data['videofile'] is None
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert 'videofile' in js_settings_json
    assert js_settings_json['videofile'] is None


def test_video_uswitch(admin_client, video, videofileHLS, mocker, settings):  # pylint: disable=redefined-outer-name
    """Test video detail page when Video.multiangle is True"""
    settings.USWITCH_URL = 'https://testing_odl.mit.edu'
    mocker.patch('ui.utils.get_cloudfront_signed_url', return_value=videofileHLS.cloudfront_url)
    video.status = 'Complete'
    video.multiangle = True
    video.save()
    url = reverse('video-uswitch', kwargs={'pk': video.id})
    response = admin_client.get(url)
    assert response.context_data['uswitchPlayerURL'] == 'https://testing_odl.mit.edu'
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        'videofile': {
            'src': response.context_data['videofile'].cloudfront_url,
            'title': video.title,
            'description': video.description,
        },
        'uswitchPlayerURL': 'https://testing_odl.mit.edu',
        'gaTrackingID': settings.GA_TRACKING_ID,
        'public_path': '/static/bundles/'
    }


def test_mosaic_view(admin_client, settings):  # pylint: disable=redefined-outer-name
    """Test the MosaicView"""
    settings.USWITCH_URL = 'https://testing_odl.mit.edu'
    url = reverse('video-mosaic')
    response = admin_client.get(url)
    assert response.context_data['uswitchPlayerURL'] == 'https://testing_odl.mit.edu'
