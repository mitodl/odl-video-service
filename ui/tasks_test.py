"""Task tests"""

import pytest
import requests

from ui import tasks


@pytest.mark.django_db
def test_post_video_to_edx(mocker):
    """post_video_to_edx task should load a Video and call an internal API function to post to edX"""
    patched_api_method = mocker.patch(
        "ui.tasks.ovs_api.post_video_to_edx", return_value={}
    )
    vf_2 = mocker.Mock(id=2)
    vf_1 = mocker.Mock(id=1)
    queryset_mock = mocker.Mock()
    queryset_mock.select_related.return_value = [vf_2, vf_1]
    mocker.patch("ui.tasks.VideoFile.objects.filter", return_value=queryset_mock)

    tasks.post_video_to_edx.delay(999)

    patched_api_method.assert_called_once_with([vf_1, vf_2])


@pytest.mark.django_db
def test_post_video_to_edx_missing(mocker):
    """post_video_to_edx task should log an error if a Video doesn't exist with the given id"""
    patched_api_method = mocker.patch("ui.tasks.ovs_api.post_video_to_edx")
    patched_log_error = mocker.patch("ui.tasks.log.error")
    tasks.post_video_to_edx.delay(123)
    patched_log_error.assert_called_once()
    assert "doesn't exist" in patched_log_error.call_args[0][0]
    patched_api_method.assert_not_called()


@pytest.mark.django_db
def test_batch_update_video_on_edx(mocker):
    """
    batch_update_video_on_edx should call batch_update_video_on_edx_chunked for each chunk of video keys
    """
    mock_batch = mocker.patch("ui.tasks.batch_update_video_on_edx_chunked")
    group_mock = mocker.patch("ui.tasks.celery.group", autospec=True)
    all_ids = list(range(1, 101))
    tasks.batch_update_video_on_edx(all_ids, chunk_size=10)

    assert group_mock.call_count == 1
    for i in list(range(10)):
        mock_batch.assert_any_call(all_ids[i * 10 : i * 10 + 10])


def _conflict_error():
    response = type("Response", (), {"status_code": 409, "text": "conflict"})()
    return requests.exceptions.HTTPError(response=response)


@pytest.mark.django_db
def test_migrate_keycloak_groups_chunk_handles_conflict_and_errors(mocker):
    """Group chunk task should count 409s as skipped and record other failures."""
    mock_manager = mocker.Mock()
    mock_manager.create_group.side_effect = [
        {"id": "created"},
        _conflict_error(),
        _conflict_error(),
        Exception("boom"),
    ]

    mocker.patch(
        "ui.tasks.build_keycloak_manager",
        return_value=mock_manager,
    )

    result = tasks.migrate_keycloak_groups_chunk(
        ["create-me", "dup-a", "dup-b", "bad-group"],
        keycloak_config={},
    )

    assert result["created"] == 1
    assert result["existing_skipped"] == 2
    assert result["failed"] == 1
    assert len(result["errors"]) == 1


@pytest.mark.django_db
def test_migrate_keycloak_users_chunk_handles_conflict_and_errors(mocker):
    """User chunk task should count 409s as skipped and record other failures."""
    mock_manager = mocker.Mock()
    mock_manager.create_user.side_effect = [
        {"id": "created"},
        _conflict_error(),
        _conflict_error(),
        Exception("boom"),
    ]

    mocker.patch(
        "ui.tasks.build_keycloak_manager",
        return_value=mock_manager,
    )

    payload = [
        {
            "id": 1,
            "username": "create",
            "email": "create@example.com",
            "first_name": "Create",
            "last_name": "User",
        },
        {
            "id": 2,
            "username": "dup-a",
            "email": "dup-a@example.com",
            "first_name": "Dup",
            "last_name": "A",
        },
        {
            "id": 3,
            "username": "dup-b",
            "email": "dup-b@example.com",
            "first_name": "Dup",
            "last_name": "B",
        },
        {
            "id": 4,
            "username": "bad",
            "email": "bad@example.com",
            "first_name": "Bad",
            "last_name": "User",
        },
    ]

    result = tasks.migrate_keycloak_users_chunk(
        payload,
        keycloak_config={},
        default_password="ChangeMe123!",
    )

    assert result["created"] == 1
    assert result["existing_skipped"] == 2
    assert result["invalid_skipped"] == 0
    assert result["failed"] == 1
    assert len(result["errors"]) == 1


@pytest.mark.django_db
def test_migrate_keycloak_users_chunk_skips_invalid_payload(mocker):
    """Task should skip malformed user payload entries and continue."""
    mock_manager = mocker.Mock()
    mock_manager.create_user.return_value = {"id": "created"}

    mocker.patch(
        "ui.tasks.build_keycloak_manager",
        return_value=mock_manager,
    )

    payload = [
        {
            "id": 1,
            "username": "ok",
            "email": "ok@example.com",
            "first_name": "Ok",
            "last_name": "User",
        },
        {
            "id": 2,
            "username": "",
            "email": "",
            "first_name": "Bad",
            "last_name": "User",
        },
    ]

    result = tasks.migrate_keycloak_users_chunk(
        payload,
        keycloak_config={},
        default_password="ChangeMe123!",
    )

    assert result["created"] == 1
    assert result["invalid_skipped"] == 1
    assert result["failed"] == 0
