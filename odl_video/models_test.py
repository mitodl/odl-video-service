"""
Tests for odl_video.models
"""
import pytest

from odl_video.models import TimestampedModelQuerySet


@pytest.mark.parametrize('include_updated_at', [True, False])
def test_timestamped_model_query_set_update(mocker, include_updated_at):
    """
    Tests that youtube_id is only returned if the status is 'processed'
    """
    patched_QuerySet_update = mocker.patch('django.db.models.query.QuerySet.update')
    patched_now = mocker.patch('odl_video.models.now_in_utc')
    queryset = TimestampedModelQuerySet()
    kwargs = {'some': 'value'}
    if include_updated_at:
        kwargs['updated_at'] = 'some_value'
    queryset.update(**kwargs)
    if include_updated_at:
        expected_super_kwargs = kwargs
    else:
        expected_super_kwargs = {**kwargs, "updated_at": patched_now.return_value}
    assert patched_QuerySet_update.call_args[1] == expected_super_kwargs
