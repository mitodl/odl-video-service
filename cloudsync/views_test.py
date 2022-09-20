"""tests for cloudsync views"""
import pytest
from django.test import Client
from django.urls import reverse

from ui.factories import UserFactory

# pylint:disable=redefined-outer-name
pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    """DRF API anonymous test client"""
    return Client()


def test_youtube_token_initial_get(mocker, client):
    """User should be redirected to an authentication url"""
    client.force_login(UserFactory.create(is_staff=True))
    mock_flow = mocker.patch(
        "cloudsync.views.InstalledAppFlow.from_client_config",
        return_value=mocker.Mock(
            credentials=mocker.Mock(token="a", refresh_token="b"),
            authorization_url=mocker.Mock(return_value=("https://fake.edu", "")),
        ),
    )
    client.get(reverse("yt_tokens"), follow=True)
    mock_flow.return_value.authorization_url.assert_called_once()


def test_youtube_token_callback(mocker, client):
    """User should receive access and refresh tokens"""
    mock_flow = mocker.patch(
        "cloudsync.views.InstalledAppFlow.from_client_config",
        return_value=mocker.Mock(credentials=mocker.Mock(token="a", refresh_token="b")),
    )
    client.force_login(UserFactory.create(is_staff=True))
    response = client.get(f"{reverse('yt_tokens')}?code=abcdef")
    mock_flow.return_value.fetch_token.assert_called_once()
    assert response.json() == {"YT_ACCESS_TOKEN": "a", "YT_REFRESH_TOKEN": "b"}


def test_youtube_token_admins_only(client):
    """A non-admin user should get a 403"""
    client.force_login(UserFactory.create())
    response = client.get(reverse("yt_tokens"), follow=True)
    assert response.status_code == 403
