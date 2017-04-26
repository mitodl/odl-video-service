
def test_index_anonymous(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'login_form' in response.context_data
    assert 'register_form' in response.context_data
    assert response.template_name == ['ui/index.html']


def test_upload_anonymous(client):
    response = client.get('/upload/')
    assert response.status_code == 302
    assert response['Location'] == '/login/?next=/upload/'


def test_upload(client, user):
    client.force_login(user)
    response = client.get('/upload/')
    assert response.status_code == 302
    assert response['Location'] == '/login/?next=/upload/'


def test_upload_admin(admin_client, mocker):
    mocker.patch(
        'ui.views.get_dropbox_credentials',
        return_value=('dbkey', 'dbsecret')
    )
    response = admin_client.get('/upload/')
    assert response.status_code == 200
    assert response.context_data['dropbox_key'] == 'dbkey'
    assert response.template_name == ['ui/upload.html']
