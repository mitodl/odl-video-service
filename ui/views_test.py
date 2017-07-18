"""
Tests for views
"""
import json

from django.conf import settings
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


def test_upload_admin(admin_client, mocker):
    """Test upload admin"""
    mocker.patch(
        'ui.views.get_dropbox_credentials',
        return_value=('dbkey', 'dbsecret')
    )
    response = admin_client.get('/upload/')
    assert response.status_code == 200
    assert response.context_data['dropbox_key'] == 'dbkey'
    assert response.template_name == ['ui/upload.html']


def test_video_detail_hls(admin_client, video, videofileHLS, mocker):  # pylint: disable=unused-argument
    """Test video detail page when HLS videofile is available"""
    mocker.patch('ui.models.make_cloudfront_signed_url', return_value=videofileHLS.cloudfront_url)
    video.status = 'Complete'
    url = reverse('video-detail', kwargs={'pk': video.id})
    response = admin_client.get(url)
    assert 'videofile' in response.context_data
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        'videofile': response.context_data['videofile'].cloudfront_signed_url,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": '/static/bundles/'
    }


def test_video_detail_unencoded(admin_client, video_unencoded,
                                videofile_unencoded, mocker):  # pylint: disable=unused-argument
    """Test video detail page when HLS videofile is not available"""
    mocker.patch('ui.models.make_cloudfront_signed_url', return_value=videofile_unencoded.cloudfront_url)
    url = reverse('video-detail', kwargs={'pk': video_unencoded.id})
    video_unencoded.status = 'Complete'
    response = admin_client.get(url)
    assert 'videofile' in response.context_data
    assert response.context_data['videofile'] is None
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert 'videofile' in js_settings_json
    assert js_settings_json['videofile'] == ''
