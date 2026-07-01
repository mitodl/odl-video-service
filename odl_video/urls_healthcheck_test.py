"""Tests for the healthcheck urls"""

import pytest
from django.urls import get_resolver
from health_check.views import HealthCheckView


@pytest.mark.parametrize(
    "path",
    [
        "/health/",
        "/health/startup/",
        "/health/liveness/",
        "/health/readiness/",
        "/health/full/",
    ],
)
def test_healthcheck_urls_resolve(path):
    """All healthcheck endpoints should resolve to HealthCheckView"""
    # Resolve directly against this urlconf module rather than django.urls.resolve()
    # (which would walk the full project urlconf) to keep this test scoped to what
    # it actually needs to exercise.
    match = get_resolver("odl_video.urls_healthcheck").resolve(path)
    assert match.func.view_class is HealthCheckView
