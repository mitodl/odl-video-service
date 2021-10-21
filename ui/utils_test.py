"""Tests for utils methods"""
from tempfile import NamedTemporaryFile
import json

import pytest
from django.contrib.auth.models import AnonymousUser
from zeep.exceptions import Fault

from odl_video.test_utils import MockResponse
from ui import factories
from ui.exceptions import MoiraException, GoogleAnalyticsException
from ui.utils import (
    write_to_file,
    MOIRA_CACHE_KEY,
    get_moira_client,
    query_moira_lists,
    user_moira_lists,
    has_common_lists,
    get_video_analytics,
    get_google_analytics_client,
    generate_google_analytics_query,
    parse_google_analytics_response,
    generate_mock_video_analytics_data,
    list_members,
    multi_urljoin,
    partition,
    partition_to_lists,
    get_error_response_summary_dict,
    send_refresh_request,
)

# pylint: disable=unused-argument,too-many-arguments

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "key_file, cert_file",
    [
        (NamedTemporaryFile(), None),
        (None, NamedTemporaryFile()),
        (None, None),
    ],
)
def test_get_moira_client_missing_secrets(mock_moira, settings, key_file, cert_file):
    """Test that the correct error is returned if a key file is missing"""
    settings.MIT_WS_PRIVATE_KEY_FILE = (
        "bad/file/path" if not key_file else key_file.name
    )
    settings.MIT_WS_CERTIFICATE_FILE = (
        "bad/file/path" if not cert_file else cert_file.name
    )
    with pytest.raises(RuntimeError) as err:
        get_moira_client()
        assert not mock_moira.called
        if key_file is None:
            assert settings.MIT_WS_PRIVATE_KEY_FILE in str(err)
        if cert_file is None:
            assert settings.MIT_WS_CERTIFICATE_FILE in str(err)


def test_get_moira_client_success(mock_moira, settings):
    """Test that a client is returned from get_moira_client"""
    tempfile1, tempfile2 = (NamedTemporaryFile(), NamedTemporaryFile())
    settings.MIT_WS_PRIVATE_KEY_FILE = tempfile1.name
    settings.MIT_WS_CERTIFICATE_FILE = tempfile2.name
    get_moira_client()
    assert mock_moira.called_once_with(
        settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE
    )


def test_write_to_file():
    """Test that write_to_file creates a file with the correct contents"""
    content = b"-----BEGIN CERTIFICATE-----\nMIID5DCCA02gAwIBAgIRTUTVwsj4Vy+l6+XTYjnIQ==\n-----END CERTIFICATE-----"
    with NamedTemporaryFile() as outfile:
        write_to_file(outfile.name, content)
        with open(outfile.name, "rb") as infile:
            assert infile.read() == content


def test_query_moira_lists(mock_moira_client):
    """
    Test that expected lists are returned.
    """
    list_names = ["test_moira_list01", "test_moira_list02"]
    mock_moira_client.return_value.user_list_membership.return_value = [
        {"listName": list_name} for list_name in list_names
    ]
    other_user = factories.UserFactory(email="someone@mit.edu")
    assert query_moira_lists(other_user) == list_names


def test_query_moira_lists_no_lists(mock_moira_client):
    """
    Test that an empty list is returned if Moira throws a java NPE
    """
    mock_moira_client.return_value.user_list_membership.side_effect = Fault(
        "java.lang.NullPointerException"
    )
    other_user = factories.UserFactory(email="someone@mit.edu")
    assert query_moira_lists(other_user) == []


def test_query_moira_lists_error(mock_moira_client):
    """
    Test that a Moira exception is raised if moira client call fails with anything other than a java NPE
    """
    mock_moira_client.return_value.user_list_membership.side_effect = Fault(
        "Not a java NPE"
    )
    with pytest.raises(MoiraException):
        query_moira_lists(factories.UserFactory())


def test_user_moira_lists_cache_hit(mocker):
    """
    Test that returns from cache if cache has lists.
    """
    mock_cache = mocker.patch("ui.utils.cache")
    mock_query_moira_lists = mocker.patch("ui.utils.query_moira_lists")
    cached_list_names = set(["some_list"])
    mock_cache.get.return_value = cached_list_names
    result = user_moira_lists(factories.UserFactory())
    assert result == cached_list_names
    assert not mock_query_moira_lists.called


def test_user_moira_lists_cache_miss(mocker, settings):
    """
    Test that queries and caches lists if not already in cache.
    """
    mock_cache = mocker.patch("ui.utils.cache")
    mock_query_moira_lists = mocker.patch("ui.utils.query_moira_lists")
    mock_cache.get.return_value = None
    user = factories.UserFactory()
    assert not mock_query_moira_lists.called
    assert not mock_cache.set.called
    result = user_moira_lists(user)
    expected_result = set(mock_query_moira_lists.return_value)
    assert result == expected_result
    assert mock_query_moira_lists.called_once_with(user)
    assert mock_cache.set.called_once_with(
        MOIRA_CACHE_KEY.format(user_id=user.id),
        expected_result,
        settings.MOIRA_CACHE_TIMEOUT,
    )


def test_user_moira_lists_anonymous():
    """
    Test that empty set is returned for anonymous user
    """
    assert user_moira_lists(AnonymousUser()) == set()


def test_has_common_lists(mocker):
    """
    Test that has_common_lists returns the correct boolean value
    """
    mock_user_moira_lists = mocker.patch("ui.utils.user_moira_lists")
    mock_user_moira_lists.return_value = set(["a", "b"])
    user = factories.UserFactory()
    assert has_common_lists(user, ["b", "c"]) is True
    assert has_common_lists(user, ["c"]) is False


def test_get_video_analytics(mocker):
    """Test that video analytics data is returned"""
    mock_get_ga_client = mocker.patch("ui.utils.get_google_analytics_client")
    mock_generate_ga_query = mocker.patch("ui.utils.generate_google_analytics_query")
    mock_parse_ga_response = mocker.patch("ui.utils.parse_google_analytics_response")
    video = factories.VideoFactory()
    result = get_video_analytics(video)
    expected_ga_client = mock_get_ga_client.return_value
    expected_batchGet_call = expected_ga_client.reports.return_value.batchGet
    expected_ga_query = mock_generate_ga_query.return_value
    assert expected_batchGet_call.called_once_with(body=expected_ga_query)
    assert mock_parse_ga_response.called_once_with(expected_batchGet_call.return_value)
    assert result is mock_parse_ga_response.return_value


def test_get_video_analytics_parse_failure(mocker):
    """Test that video analytics data is returned"""
    mocker.patch("ui.utils.get_google_analytics_client")
    mocker.patch("ui.utils.generate_google_analytics_query")
    mock_parse_ga_response = mocker.patch("ui.utils.parse_google_analytics_response")
    mock_parse_ga_response.side_effect = Exception("badness")
    video_key = "some_video_key"
    with pytest.raises(GoogleAnalyticsException):
        get_video_analytics(video_key)


def test_get_google_analytics_client_success(ga_client_mocks, settings):
    """Test that a client is returned from get_ga_client"""
    settings.GA_KEYFILE_JSON = '{"some": "json"}'
    result = get_google_analytics_client()
    assert (
        ga_client_mocks["ServiceAccountCredentials"].from_json_keyfile_dict
    ).called_once_with(json.loads(settings.GA_KEYFILE_JSON))
    assert ga_client_mocks["build"].called_once_with(
        ga_client_mocks["ServiceAccountCredentials"].from_json_keyfile_dict.return_value
    )
    assert result is ga_client_mocks["build"].return_value


@pytest.mark.parametrize("multiangle", [True, False])
def test_generate_google_analytics_query_success(settings, multiangle):
    """Test that expected query is generated."""
    video = factories.VideoFactory(multiangle=multiangle)
    ga_view_id = "some_view_id"
    settings.GA_VIEW_ID = ga_view_id
    ga_dimension_camera = "some_camera_dimension"
    settings.GA_DIMENSION_CAMERA = ga_dimension_camera
    actual_query = generate_google_analytics_query(video)
    expected_dimensions = [{"name": "ga:eventAction"}]
    if multiangle:
        expected_dimensions.append({"name": "ga:" + ga_dimension_camera})
    expected_query = {
        "reportRequests": [
            {
                "viewId": ga_view_id,
                "dateRanges": [
                    {
                        "startDate": "2005-01-01",
                        "endDate": "9999-01-01",
                    }
                ],
                "metrics": [{"expression": "ga:totalEvents"}],
                "dimensions": expected_dimensions,
                "dimensionFilterClauses": [
                    {
                        "filters": [
                            {
                                "dimensionName": "ga:eventLabel",
                                "operator": "EXACT",
                                "expressions": [video.hexkey.capitalize()],
                            },
                        ],
                    },
                ],
            },
        ],
    }
    assert actual_query == expected_query


def test_parse_google_analytics_response_multiangle():
    """Test that parse result matches expected result."""
    mock_response = {
        "reports": [
            {
                "columnHeader": {
                    "dimensions": ["ga:eventAction", "ga:dimension1"],
                    "metricHeader": {
                        "metricHeaderEntries": [
                            {"name": "ga:totalEvents", "type": "INTEGER"},
                        ]
                    },
                },
                "data": {
                    "maximums": [{"values": ["2"]}],
                    "minimums": [{"values": ["1"]}],
                    "rowCount": 5,
                    "rows": [
                        {
                            "dimensions": ["changeCameraView", "camera2"],
                            "metrics": [{"values": ["16"]}],
                        },
                        {
                            "dimensions": ["Pause", "camera1"],
                            "metrics": [{"values": ["4"]}],
                        },
                        {
                            "dimensions": ["T0000", "camera1"],
                            "metrics": [{"values": ["102"]}],
                        },
                        {
                            "dimensions": ["T0002", "camera1"],
                            "metrics": [{"values": ["98"]}],
                        },
                        {
                            "dimensions": ["T0002", "camera2"],
                            "metrics": [{"values": ["3"]}],
                        },
                        {
                            "dimensions": ["T0002", "Bad channel"],
                            "metrics": [{"values": ["3"]}],
                        },
                    ],
                    "totals": [{"values": ["30"]}],
                },
            }
        ]
    }
    expected_result = {
        "times": [0, 2],
        "channels": ["camera1", "camera2"],
        "is_multichannel": True,
        "views_at_times": {
            0: {
                "camera1": 102,
            },
            2: {
                "camera1": 98,
                "camera2": 3,
            },
        },
    }
    actual_result = parse_google_analytics_response(mock_response)
    assert actual_result == expected_result


def test_parse_google_analytics_response_singlecam():
    """Test that parse result matches expected result."""
    mock_response = {
        "reports": [
            {
                "columnHeader": {
                    "dimensions": ["ga:eventAction"],
                    "metricHeader": {
                        "metricHeaderEntries": [
                            {"name": "ga:totalEvents", "type": "INTEGER"},
                        ]
                    },
                },
                "data": {
                    "maximums": [{"values": ["2"]}],
                    "minimums": [{"values": ["1"]}],
                    "rowCount": 5,
                    "rows": [
                        {
                            "dimensions": ["changeCameraView"],
                            "metrics": [{"values": ["16"]}],
                        },
                        {"dimensions": ["Pause"], "metrics": [{"values": ["4"]}]},
                        {"dimensions": ["T0000"], "metrics": [{"values": ["102"]}]},
                        {"dimensions": ["T0002"], "metrics": [{"values": ["98"]}]},
                    ],
                    "totals": [{"values": ["30"]}],
                },
            }
        ]
    }
    expected_result = {
        "times": [0, 2],
        "channels": ["views"],
        "is_multichannel": False,
        "views_at_times": {
            0: {
                "views": 102,
            },
            2: {
                "views": 98,
            },
        },
    }
    actual_result = parse_google_analytics_response(mock_response)
    assert actual_result == expected_result


@pytest.mark.parametrize(
    "n, seed, expected",
    [
        (
            1,
            "some seed",
            {
                "channels": ["camera1", "camera2", "camera3", "camera4"],
                "times": [0],
                "views_at_times": {
                    0: {"camera1": 86, "camera2": 83, "camera3": 0, "camera4": 82}
                },
            },
        ),
        (
            2,
            "some other seed",
            {
                "channels": ["camera1", "camera2", "camera3", "camera4"],
                "times": [0, 1],
                "views_at_times": {
                    0: {"camera1": 35, "camera2": 63, "camera3": 0, "camera4": 64},
                    1: {"camera1": 97, "camera2": 98, "camera3": 7, "camera4": 33},
                },
            },
        ),
    ],
)
def test_generate_mock_video_analytics_data(n, seed, expected):
    """Test that returns expected result."""
    actual = generate_mock_video_analytics_data(n=n, seed=seed)
    assert actual == expected


def test_list_members_exception(mock_moira_client):
    """
    Test that a Moira exception is raised if moira client call fails with anything other than a java NPE
    """
    mock_moira_client.return_value.list_members.side_effect = Exception("exception")
    with pytest.raises(MoiraException):
        list_members(factories.UserFactory())


@pytest.mark.parametrize(
    "url_base,url_parts,trailing,expected",
    [
        ("http://mit.edu", ["a", "b"], False, "http://mit.edu/a/b"),
        ("http://mit.edu", ["a", "b/c/d", "e"], False, "http://mit.edu/a/b/c/d/e"),
        ("http://mit.edu/", ["/a/", "/b"], False, "http://mit.edu/a/b"),
        ("http://mit.edu", ["a", "b"], True, "http://mit.edu/a/b/"),
        ("http://mit.edu", ["a", "b/"], False, "http://mit.edu/a/b/"),
    ],
)
def test_multi_urljoin(url_base, url_parts, trailing, expected):
    """multi_urljoin should construct a valid URL from a base string and an arbitrary number of URL parts"""
    assert multi_urljoin(url_base, *url_parts, add_trailing_slash=trailing) == expected


def test_partition():
    """
    Assert that partition splits an iterable into two iterables according to a condition
    """
    nums = [1, 2, 1, 3, 1, 4, 0, None, None]
    not_ones, ones = partition(nums, lambda n: n == 1)
    assert list(not_ones) == [2, 3, 4, 0, None, None]
    assert list(ones) == [1, 1, 1]
    # The default predicate is the standard Python bool() function
    falsey, truthy = partition(nums)
    assert list(falsey) == [0, None, None]
    assert list(truthy) == [1, 2, 1, 3, 1, 4]


def test_partition_to_lists():
    """
    Assert that partition_to_lists splits an iterable into two lists according to a condition
    """
    nums = [1, 2, 1, 3, 1, 4, 0, None, None]
    not_ones, ones = partition_to_lists(nums, lambda n: n == 1)
    assert not_ones == [2, 3, 4, 0, None, None]
    assert ones == [1, 1, 1]
    # The default predicate is the standard Python bool() function
    falsey, truthy = partition_to_lists(nums)
    assert falsey == [0, None, None]
    assert truthy == [1, 2, 1, 3, 1, 4]


@pytest.mark.parametrize(
    "content,content_type,exp_summary_content",
    [
        ['{"bad": "response"}', "application/json", '{"bad": "response"}'],
        ["plain text", "text/plain", "plain text"],
        ["<div>HTML content</div>", "text/html; charset=utf-8", "(HTML body ignored)"],
    ],
)
def test_get_error_response_summary(content, content_type, exp_summary_content):
    """
    get_error_response_summary should provide a summary of an error HTTP response object with the correct bits of
    information depending on the type of content.
    """
    status_code = 400
    url = "http://example.com"
    mock_response = MockResponse(
        status_code=status_code, content=content, content_type=content_type, url=url
    )
    assert get_error_response_summary_dict(mock_response) == {
        "content": exp_summary_content,
        "url": url,
        "code": status_code,
    }


def test_send_refresh_request(mocker):
    """
    send_refresh_request should send a post request with clint_id and client_secret
    to get a new JWT access token
    """
    client_secret = "secrets"
    client_id = "clientid"
    url = "http://test.url"
    mock_post = mocker.patch("ui.utils.requests.post")
    send_refresh_request(url, client_id, client_secret)
    expected_token_url = "{}/oauth2/access_token/".format(url)
    expected_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "token_type": "JWT",
    }
    mock_post.assert_called_once_with(expected_token_url, data=expected_data)
