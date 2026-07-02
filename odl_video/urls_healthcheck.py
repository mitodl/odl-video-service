"""Healthcheck urls"""

from django.urls import include, path
from health_check.views import HealthCheckView

MIGRATIONS_CHECK = "health_check.contrib.migrations.backends.MigrationsHealthCheck"

BASE_CHECKS = [
    # "default" is in-memory and always available; "redis" is the real backing cache.
    ("health_check.Cache", {"alias": "redis"}),
    "health_check.Database",
    "health_check.contrib.redis.Redis",
]

urlpatterns = [
    path(
        "health/",
        include(
            [
                path(
                    "",
                    HealthCheckView.as_view(
                        checks=[
                            *BASE_CHECKS,
                            MIGRATIONS_CHECK,
                            "health_check.contrib.celery.Ping",
                        ]
                    ),
                ),
                path(
                    "startup/",
                    HealthCheckView.as_view(checks=[*BASE_CHECKS, MIGRATIONS_CHECK]),
                ),
                path(
                    "liveness/",
                    HealthCheckView.as_view(checks=["health_check.Database"]),
                ),
                path(
                    "readiness/",
                    HealthCheckView.as_view(checks=[*BASE_CHECKS]),
                ),
                path(
                    "full/",
                    HealthCheckView.as_view(
                        checks=[
                            *BASE_CHECKS,
                            MIGRATIONS_CHECK,
                            "health_check.contrib.celery.Ping",
                        ]
                    ),
                ),
            ]
        ),
    ),
]
