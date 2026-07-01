# This file was originally scaffolded by django-aqueduct:
#
#   uv run python manage.py generate_aqueduct_settings \
#       --modules odl_video.settings --include-envparser \
#       --output odl_video/aqueduct_settings.py
#
# ...and then hand-refined. Re-running the generator will overwrite the hand
# written parts below (required fields, model_validators, imports) so treat
# this file as source-controlled, not disposable output.
#
# Known limitations (fields intentionally left as static generation-time
# snapshots rather than fully re-derived):
#   * INSTALLED_APPS / MIDDLEWARE / AUTHENTICATION_BACKENDS / LOGIN_URL do not
#     re-branch on USE_KEYCLOAK or DEBUG the way odl_video/settings.py does
#     (conditionally appending social_django / nplusone). They reflect the
#     production defaults (USE_KEYCLOAK=True, DEBUG=False).
#   * CELERY_BEAT_SCHEDULE's per-task frequencies (VIDEO_STATUS_UPDATE_FREQUENCY,
#     VIDEO_WATCH_BUCKET_FREQUENCY, YT_UPLOAD_FREQUENCY,
#     STUCK_UPLOADING_CHECK_FREQUENCY, SCHEDULE_RETRANSCODE_FREQUENCY) are only
#     ever read inline in odl_video/settings.py, never assigned to a module
#     global, so django-aqueduct's module inspector cannot discover them as
#     fields. The schedule below is a static snapshot; it also omits the
#     conditional "schedule_retranscodes" entry (gated on
#     FEATURES["RETRANSCODE_ENABLED"]) and the dev-only "update-statuses" entry
#     is baked in since ENVIRONMENT defaults to "dev".
#   * NPLUSONE_LOGGER is a live `logging.Logger` instance — not a serialisable
#     setting — left as `None`; nplusone's own middleware looks up its logger
#     by name regardless of this setting.
#   * LOGGING is intentionally NOT modelled as a Pydantic field. It is built by
#     `mitol.observability.settings.logging` via a factory function that reads
#     `django.conf.settings.DEBUG` at logging-configuration time (after Django
#     settings are fully loaded), so a static default would be wrong as soon
#     as DEBUG differs from the value observed when this file was generated.
#     The settings_aqueduct*.py shims re-import it the same way
#     odl_video/settings.py does, via `import_settings_modules`.

from __future__ import annotations

import pathlib
import platform
from typing import Any
from urllib.parse import urljoin

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from odl_video.envs import get_any

# odl_video/settings.py computes BASE_DIR as the parent of the odl_video
# package directory (`dirname(dirname(abspath(__file__)))` from within
# odl_video/settings.py). This module lives in the same package, so the same
# computation applies unchanged. Recomputing it here (instead of baking in the
# absolute path captured at generation time) keeps this file portable across
# machines/containers.
_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
_DEFAULT_BASE_DIR = str(_PACKAGE_DIR.parent)


class AqueductSettings(BaseSettings):
    """Typed Django settings model mirroring odl_video/settings.py.

    Populate from environment variables (the default source), or layer in
    additional `pydantic_settings` sources (Vault, AWS SSM, YAML, ...) by
    overriding `settings_customise_sources` — see `DevAqueductSettings` below.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="allow",
    )

    # ===== mitol.transcoding.settings.job (via EnvParser) =====
    # VIDEO_S3_TRANSCODE_BUCKET, VIDEO_S3_TRANSCODE_PREFIX, and
    # VIDEO_S3_THUMBNAIL_BUCKET are also assigned directly in
    # odl_video/settings.py (see the "odl_video.settings" section below),
    # which is what actually ends up on the settings module at runtime — so
    # they are modelled once, there, rather than duplicated here.
    POST_TRANSCODE_ACTIONS: list[Any] = Field(
        default_factory=list, description="Actions to perform before publish"
    )
    TRANSCODE_JOB_TEMPLATE: str = Field(
        default="", description="Path to the transcoding job template"
    )
    VIDEO_S3_THUMBNAIL_PREFIX: str = Field(
        default="", description="Prefix for the thumbnail video"
    )
    VIDEO_S3_TRANSCODE_ENDPOINT: str = Field(
        default="aws_mediaconvert_transcodes",
        description="Endpoint to be used for AWS MediaConvert",
    )
    VIDEO_S3_UPLOAD_PREFIX: str = Field(
        default="", description="Prefix for the source video"
    )
    VIDEO_TRANSCODE_QUEUE: str = Field(
        default="Default",
        description="Name of MediaConvert queue to use for transcoding",
    )

    # ===== odl_video.settings =====
    ADMINS: tuple[tuple[str, str], ...] = Field(default=())  # DERIVED: see validator
    ADMIN_EMAIL: str = Field(default="")
    ADWORDS_CONVERSION_ID: str = Field(default="")
    ALLOWED_HOSTS: list[Any] = Field(default_factory=lambda: ["*"])
    AUTHENTICATION_BACKENDS: list[Any] = Field(
        default_factory=lambda: ["social_core.backends.keycloak.KeycloakOAuth2"]
    )
    # ----- MANDATORY_SETTINGS (odl_video/settings.py ~451-486): these had no
    # meaningful default upstream (falsy "" / None) and were only guarded by
    # ui.apps.UIConfig.ready() at Django-app-ready time. They are modelled as
    # required (no default) here so a missing value fails fast at settings
    # instantiation instead. MANDATORY_SETTINGS/ENFORCE_MANDATORY_SETTINGS
    # themselves are kept below (unchanged) purely because ui.apps.UIConfig
    # still reads them at runtime; the check they perform is now redundant
    # but harmless.
    AWS_ACCESS_KEY_ID: str = Field()
    AWS_ACCOUNT_ID: str = Field()
    AWS_REGION: str = Field()
    AWS_ROLE_NAME: str = Field()
    AWS_S3_DOMAIN: str = Field(default="s3.amazonaws.com")
    AWS_S3_UPLOAD_IO_CHUNKSIZE_KB: int = Field(default=256)
    AWS_S3_UPLOAD_MAX_CONCURRENCY: int = Field(default=10)
    AWS_S3_UPLOAD_MAX_IO_QUEUE: int = Field(default=100)
    AWS_S3_UPLOAD_MULTIPART_CHUNKSIZE_MB: int = Field(default=32)
    AWS_S3_UPLOAD_MULTIPART_THRESHOLD_MB: int = Field(default=32)
    AWS_S3_UPLOAD_NUM_DOWNLOAD_ATTEMPTS: int = Field(default=5)
    AWS_S3_UPLOAD_TRANSFER_CONFIG: dict[str, Any] = Field(
        default_factory=dict
    )  # DERIVED: see validator
    AWS_S3_UPLOAD_USE_THREADS: bool = Field(default=True)
    AWS_SECRET_ACCESS_KEY: str = Field()
    # AWS_STORAGE_BUCKET_NAME has no env var of its own — odl_video/settings.py
    # chain-assigns it from VIDEO_S3_BUCKET (`VIDEO_S3_BUCKET =
    # AWS_STORAGE_BUCKET_NAME = get_string("VIDEO_S3_BUCKET", "")`).
    AWS_STORAGE_BUCKET_NAME: str = Field(default="")  # DERIVED: see validator
    AWS_TRANSCODE_BUCKET_NAME: str = Field(default="")
    BASE_DIR: str = Field(default_factory=lambda: _DEFAULT_BASE_DIR)
    CACHES: dict[str, Any] = Field(
        default_factory=lambda: {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "local-in-memory-cache",
            },
            "redis": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": None,  # DERIVED: see validator
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "CONNECTION_POOL_KWARGS": {"max_connections": None},
                },
            },
        }
    )
    CELERY_ACCEPT_CONTENT: list[Any] = Field(default_factory=lambda: ["json"])
    CELERY_BEAT_SCHEDULE: dict[str, Any] = Field(
        default_factory=lambda: {
            "update-youtube-statuses": {
                "task": "cloudsync.tasks.update_youtube_statuses",
                "schedule": 60,
            },
            "watch-bucket": {
                "task": "cloudsync.tasks.monitor_watch_bucket",
                "schedule": 900,
            },
            "upload_youtube_videos": {
                "task": "cloudsync.tasks.upload_youtube_videos",
                "schedule": 3600,
            },
            "fail-stuck-uploading-videos": {
                "task": "cloudsync.tasks.fail_stuck_uploading_videos",
                "schedule": 3600,
            },
            # dev-only entry from odl_video/settings.py — baked in since
            # ENVIRONMENT defaults to "dev". See module limitations above.
            "update-statuses": {
                "task": "cloudsync.tasks.update_video_statuses",
                "schedule": 10,
            },
        }
    )
    CELERY_BEAT_SCHEDULER: Any = Field(
        default=None
    )  # DERIVED (class reference): see validator
    CELERY_BROKER_TRANSPORT_OPTIONS: dict[str, Any] = Field(
        default_factory=dict
    )  # DERIVED: see validator
    CELERY_BROKER_URL: str | None = Field(
        default=None
    )  # DERIVED (falls back to REDIS_URL): see validator
    CELERY_BROKER_VISIBILITY_TIMEOUT: int = Field(default=3600)
    CELERY_REDBEAT_REDIS_URL: str | None = Field(
        default=None
    )  # DERIVED (mirrors CELERY_BROKER_URL): see validator
    CELERY_REDIS_MAX_CONNECTIONS: int = Field(
        default=65000
    )  # DERIVED (mirrors REDIS_MAX_CONNECTIONS): see validator
    CELERY_RESULT_BACKEND: str | None = Field(
        default=None
    )  # DERIVED (mirrors REDIS_URL): see validator
    CELERY_RESULT_SERIALIZER: str = Field(default="json")
    CELERY_TASK_ALWAYS_EAGER: bool = Field(default=False)
    CELERY_TASK_EAGER_PROPAGATES: bool = Field(default=True)
    CELERY_TASK_SEND_SENT_EVENT: bool = Field(default=True)
    CELERY_TASK_SERIALIZER: str = Field(default="json")
    CELERY_TASK_TRACK_STARTED: bool = Field(default=True)
    CELERY_TIMEZONE: str = Field(default="UTC")
    # STATIC_CLOUDFRONT_DIST env var populates CLOUDFRONT_DIST (name mismatch
    # is intentional and matches odl_video/settings.py).
    CLOUDFRONT_DIST: str | None = Field(default=None)
    CLOUDFRONT_KEY_ID: str = Field()
    CLOUDFRONT_PRIVATE_KEY: bytes = Field()
    CLOUDSYNC_STREAM_S3_LOCK_TTL: int = Field(default=120)
    CLOUDSYNC_STREAM_S3_MAX_RETRIES: int = Field(default=2)
    CLOUDSYNC_STREAM_S3_RETRY_BACKOFF: int = Field(default=60)
    CLOUDSYNC_STREAM_S3_RETRY_MAX_BACKOFF: int = Field(default=600)
    CLOUDSYNC_UPLOAD_PROGRESS_REFRESH_SECONDS: int = Field(default=60)
    # DATABASE_URL / ODL_VIDEO_DB_CONN_MAX_AGE / ODL_VIDEO_DB_DISABLE_SSL are
    # only ever read inline in odl_video/settings.py while building
    # DEFAULT_DATABASE_CONFIG, never assigned to a module global, so the
    # generator could not discover them. Added by hand so DATABASES stays
    # configurable instead of being frozen to the sqlite fallback.
    DATABASE_URL: str | None = Field(default=None)
    ODL_VIDEO_DB_CONN_MAX_AGE: int = Field(default=0)
    ODL_VIDEO_DB_DISABLE_SSL: bool = Field(default=False)
    DATABASES: dict[str, Any] = Field(default_factory=dict)  # DERIVED: see validator
    DEBUG: bool = Field(default=False)
    DEFAULT_AUTO_FIELD: str = Field(default="django.db.models.AutoField")
    DEFAULT_DATABASE_CONFIG: dict[str, Any] = Field(
        default_factory=dict
    )  # DERIVED: see validator
    DEFAULT_FROM_EMAIL: str = Field(default="webmaster@localhost")
    DISABLE_WEBPACK_LOADER_STATS: bool = Field(default=False)
    DJANGO_LOG_LEVEL: str = Field(default="INFO")
    DROPBOX_KEY: str = Field()
    DROPBOX_REFRESH_TOKEN: str = Field()
    DROPBOX_SECRET: str = Field()
    EMAIL_BACKEND: str = Field(default="django.core.mail.backends.smtp.EmailBackend")
    EMAIL_HOST: str = Field(default="localhost")
    EMAIL_HOST_PASSWORD: str = Field(default="")
    EMAIL_HOST_USER: str = Field(default="")
    EMAIL_PORT: int = Field(default=25)
    EMAIL_SUPPORT: str = Field(default="support@example.com")
    EMAIL_USE_TLS: bool = Field(default=False)
    ENABLE_VIDEO_PERMISSIONS: bool = Field(default=False)
    ENFORCE_MANDATORY_SETTINGS: bool = Field(default=True)
    ENVIRONMENT: str = Field(default="dev")
    # FEATURES is a dynamic FEATURE_*-prefix scan over the environment, not a
    # fixed set of keys — see validator.
    FEATURES: dict[str, Any] = Field(default_factory=dict)
    FIELD_ENCRYPTION_KEY: str = Field(default="")
    GA_DIMENSION_CAMERA: str = Field()
    GA_KEYFILE_JSON: str = Field()
    GA_TRACKING_ID: str = Field(default="")
    GA_VIEW_ID: str = Field()
    HEALTH_CHECK: list[Any] = Field(
        default_factory=lambda: ["CELERY", "REDIS", "POSTGRES", "CERTIFICATE"]
    )
    HIJACK_ALLOW_GET_REQUESTS: bool = Field(default=True)
    HIJACK_INSERT_BEFORE: str = Field(default="</body>")
    HIJACK_LOGOUT_REDIRECT_URL: str = Field(default="/admin/auth/user")
    HOST_IP: str = Field(default="127.0.0.1")
    HOSTNAME: str = Field(
        default_factory=lambda: platform.node().split(".")[0]
    )  # DERIVED (machine hostname at process start)
    INSTALLED_APPS: list[Any] = Field(
        default_factory=lambda: [
            "mitol.observability.apps.ObservabilityConfig",
            "ui.apps.UIConfig",
            "cloudsync.apps.CloudSyncConfig",
            "techtv2ovs",
            "mail.apps.MailConfig",
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "rest_framework",
            "django_filters",
            "hijack",
            "hijack.contrib.admin",
            "encrypted_model_fields",
            "social_django",
        ]
    )
    INTERNAL_IPS: tuple[str, ...] = Field(default=())  # DERIVED: see validator
    KB: int = Field(default=1024)
    KEYCLOAK_REALM: str = Field(default="")  # DERIVED: see validator
    KEYCLOAK_SERVER_URL: str = Field(default="")  # DERIVED: see validator
    KEYCLOAK_SVC_ADMIN: str = Field(default="odl-video-app")
    # Was previously `get_string("KEYCLOAK_SVC_ADMIN_PASSWORD",
    # "odl-video-secret-2025")` in odl_video/settings.py — a hardcoded fallback
    # secret committed to git. Made required (no default) here; the value must
    # come from the environment / Vault.
    KEYCLOAK_SVC_ADMIN_PASSWORD: str = Field()
    LANGUAGE_CODE: str = Field(default="en-us")
    LECTURE_CAPTURE_USER: str = Field()
    LOGIN_REDIRECT_URL: str = Field(default="/")
    LOGIN_URL: str = Field(default="/auth/login/keycloak/")
    LOGOUT_REDIRECT_URL: str = Field(default="/")
    LOG_LEVEL: str = Field(default="INFO")
    MAILGUN_BATCH_CHUNK_SIZE: int = Field(default=1000)
    MAILGUN_BCC_TO_EMAIL: str = Field(default="no-reply@example.com")
    MAILGUN_FROM_EMAIL: str = Field(default="no-reply@example.com")
    MAILGUN_KEY: str = Field()
    MAILGUN_RECIPIENT_OVERRIDE: str | None = Field(default=None)
    MAILGUN_URL: str = Field()
    MANDATORY_SETTINGS: list[Any] = Field(
        default_factory=lambda: [
            "AWS_ACCESS_KEY_ID",
            "AWS_REGION",
            "AWS_ACCOUNT_ID",
            "AWS_S3_DOMAIN",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_STORAGE_BUCKET_NAME",
            "AWS_ROLE_NAME",
            "CLOUDFRONT_KEY_ID",
            "CLOUDFRONT_PRIVATE_KEY",
            "DROPBOX_KEY",
            "DROPBOX_SECRET",
            "DROPBOX_REFRESH_TOKEN",
            "GA_DIMENSION_CAMERA",
            "GA_KEYFILE_JSON",
            "GA_VIEW_ID",
            "LECTURE_CAPTURE_USER",
            "MAILGUN_KEY",
            "MAILGUN_URL",
            "ODL_VIDEO_BASE_URL",
            "REDIS_URL",
            "SECRET_KEY",
            "VIDEO_CLOUDFRONT_DIST",
            "VIDEO_CDN_DISTRIBUTION_ID",
            "VIDEO_S3_BUCKET",
            "VIDEO_S3_TRANSCODE_BUCKET",
            "VIDEO_S3_THUMBNAIL_BUCKET",
            "VIDEO_S3_SUBTITLE_BUCKET",
            "VIDEO_S3_WATCH_BUCKET",
            "VIDEO_S3_TRANSCODE_PREFIX",
            "ENABLE_VIDEO_PERMISSIONS",
            "YT_ACCESS_TOKEN",
            "YT_REFRESH_TOKEN",
            "YT_CLIENT_ID",
            "YT_CLIENT_SECRET",
        ]
    )
    MB: int = Field(default=1048576)
    MIDDLEWARE: list[Any] = Field(
        default_factory=lambda: [
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "hijack.middleware.HijackUserMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "social_django.middleware.SocialAuthExceptionMiddleware",
        ]
    )
    MIDDLEWARE_FEATURE_FLAG_COOKIE_MAX_AGE_SECONDS: int = Field(default=3600)
    MIDDLEWARE_FEATURE_FLAG_COOKIE_NAME: str = Field(default="ODL_VIDEO_FEATURE_FLAGS")
    MIDDLEWARE_FEATURE_FLAG_QS_PREFIX: str | None = Field(default=None)
    NPLUSONE_LOGGER: Any = Field(default=None)  # OPAQUE: a live logging.Logger
    NPLUSONE_LOG_LEVEL: int = Field(default=40)
    ODL_VIDEO_BASE_URL: str = Field()
    ODL_VIDEO_FEATURES_PREFIX: str = Field(default="FEATURE_")
    OPENEDX_API_CLIENT_ID: str = Field(default="")
    OPENEDX_API_CLIENT_SECRET: str = Field(default="")
    PAGE_SIZE_COLLECTIONS: int = Field(default=50)
    PAGE_SIZE_MAXIMUM: int = Field(default=1000)
    PAGE_SIZE_QUERY_PARAM: str = Field(default="page_size")
    PAGE_SIZE_VIDEOS: int = Field(default=1000)
    REACT_GA_DEBUG: bool = Field(default=False)
    REDIS_MAX_CONNECTIONS: int = Field(default=65000)
    REDIS_URL: str = Field()
    REST_FRAMEWORK: dict[str, Any] = Field(
        default_factory=lambda: {
            "DEFAULT_AUTHENTICATION_CLASSES": (
                "rest_framework.authentication.BasicAuthentication",
                "rest_framework.authentication.SessionAuthentication",
            )
        }
    )
    ROOT_URLCONF: str = Field(default="odl_video.urls")
    SECRET_KEY: str = Field()
    SECURE_CROSS_ORIGIN_OPENER_POLICY: str = Field(default="same-origin-allow-popups")
    SECURE_PROXY_SSL_HEADER: tuple[str, str] = Field(
        default=("HTTP_X_FORWARDED_PROTO", "https")
    )
    SECURE_SSL_REDIRECT: bool = Field(default=True)
    SENTRY_DSN: str = Field(default="")
    SENTRY_LOG_LEVEL: str = Field(default="ERROR")
    SESSION_ENGINE: str = Field(
        default="django.contrib.sessions.backends.signed_cookies"
    )
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL: str = Field(default="")
    SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL: str = Field(default="")
    SOCIAL_AUTH_KEYCLOAK_EXTRA_DATA: list[Any] = Field(
        default_factory=lambda: ["user_groups"]
    )
    SOCIAL_AUTH_KEYCLOAK_ID_KEY: str = Field(default="email")
    SOCIAL_AUTH_KEYCLOAK_KEY: str = Field(default="")
    SOCIAL_AUTH_KEYCLOAK_LOGOUT_URL: str = Field(default="")  # DERIVED: see validator
    SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY: str = Field(default="")
    SOCIAL_AUTH_KEYCLOAK_SCOPE: list[Any] = Field(
        default_factory=lambda: ["openid", "profile", "email"]
    )
    SOCIAL_AUTH_KEYCLOAK_SECRET: str = Field(default="")
    SOCIAL_AUTH_PIPELINE: list[Any] = Field(
        default_factory=lambda: [
            "social_core.pipeline.social_auth.social_details",
            "social_core.pipeline.social_auth.social_uid",
            "social_core.pipeline.social_auth.social_user",
            "social_core.pipeline.user.get_username",
            "social_core.pipeline.user.create_user",
            "social_core.pipeline.social_auth.associate_user",
            "social_core.pipeline.social_auth.load_extra_data",
            "social_core.pipeline.user.user_details",
            "odl_video.pipeline.assign_user_groups",
        ]
    )
    SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL: bool = Field(default=True)
    STATICFILES_DIRS: tuple[str, ...] = Field(default=())  # DERIVED: see validator
    STATIC_ROOT: str = Field(default="")  # DERIVED: see validator
    STATIC_URL: str = Field(default="/static/")  # DERIVED: see validator
    AWS_S3_CUSTOM_DOMAIN: str | None = Field(
        default=None
    )  # DERIVED (missing from odl_video.settings unless CLOUDFRONT_DIST is set)
    STATUS_TOKEN: str = Field(default="")
    STUCK_UPLOADING_THRESHOLD_HOURS: int = Field(default=2)
    TEMPLATES: list[Any] = Field(
        default_factory=lambda: [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],  # DERIVED: see validator
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ]
                },
            }
        ]
    )
    THUMBNAIL_UPLOAD_MAX_HEIGHT: int = Field(default=360)
    THUMBNAIL_UPLOAD_MAX_SIZE: int = Field(default=1048576)
    THUMBNAIL_UPLOAD_MAX_WIDTH: int = Field(default=640)
    TIME_ZONE: str = Field(default="UTC")
    TRANSCODE_JOB_TEMPLATE_PORTRAIT: str = Field(
        default="config/mediaconvert_portrait.json"
    )
    UNSORTED_COLLECTION: str = Field(default="Unsorted")
    USE_CELERY: bool = Field(default=True)
    USE_I18N: bool = Field(default=True)
    USE_KEYCLOAK: bool = Field(default=True)
    USE_L10N: bool = Field(default=True)
    USE_TZ: bool = Field(default=True)
    USE_WEBPACK_DEV_SERVER: bool = Field(default=False)
    VERSION: str = Field(default="0.94.1")
    VIDEO_CDN_DISTRIBUTION_ID: str = Field()
    VIDEO_CLOUDFRONT_BASE_URL: str = Field(default="")  # DERIVED: see validator
    VIDEO_CLOUDFRONT_DIST: str = Field()
    VIDEO_S3_BUCKET: str = Field()
    VIDEO_S3_SUBTITLE_BUCKET: str = Field()
    VIDEO_S3_THUMBNAIL_BUCKET: str = Field()
    VIDEO_S3_TRANSCODE_BUCKET: str = Field()
    VIDEO_S3_TRANSCODE_PREFIX: str = Field(default="transcoded")
    VIDEO_S3_WATCH_BUCKET: str = Field()
    WEBPACK_DEV_SERVER_HOST: str = Field(default="")
    WEBPACK_DEV_SERVER_PORT: int = Field(default=8082)
    WEBPACK_LOADER: dict[str, Any] = Field(
        default_factory=lambda: {
            "DEFAULT": {
                "CACHE": True,  # DERIVED (`not DEBUG`): see validator
                "BUNDLE_DIR_NAME": "bundles/",
                "STATS_FILE": "",  # DERIVED: see validator
                "POLL_INTERVAL": 0.1,
                "TIMEOUT": None,
                "IGNORE": [r".+\.hot-update\.+", r".+\.js\.map"],
            }
        }
    )
    WSGI_APPLICATION: str = Field(default="odl_video.wsgi.application")
    YT_ACCESS_TOKEN: str = Field()
    YT_CLIENT_ID: str = Field()
    YT_CLIENT_SECRET: str = Field()
    YT_PROJECT_ID: str = Field(default="")
    YT_REFRESH_TOKEN: str = Field()
    YT_UPLOAD_LIMIT: int = Field(default=4)

    # ------------------------------------------------------------------ #
    # Cross-field validators, ported from odl_video/settings.py          #
    # ------------------------------------------------------------------ #

    @model_validator(mode="after")
    def _validate_upload_timing_windows(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~389-405."""
        if (
            self.CLOUDSYNC_UPLOAD_PROGRESS_REFRESH_SECONDS
            >= self.STUCK_UPLOADING_THRESHOLD_HOURS * 3600
        ):
            raise ImproperlyConfigured(
                "CLOUDSYNC_UPLOAD_PROGRESS_REFRESH_SECONDS must be below the "
                "janitor threshold (STUCK_UPLOADING_THRESHOLD_HOURS) or "
                "healthy uploads get reaped."
            )
        if (
            self.CLOUDSYNC_STREAM_S3_LOCK_TTL
            <= self.CLOUDSYNC_UPLOAD_PROGRESS_REFRESH_SECONDS
        ):
            raise ImproperlyConfigured(
                "CLOUDSYNC_STREAM_S3_LOCK_TTL must exceed "
                "CLOUDSYNC_UPLOAD_PROGRESS_REFRESH_SECONDS so the lock "
                "heartbeat can reacquire before the lease expires."
            )
        if self.CLOUDSYNC_STREAM_S3_LOCK_TTL >= self.CELERY_BROKER_VISIBILITY_TIMEOUT:
            raise ImproperlyConfigured(
                "CLOUDSYNC_STREAM_S3_LOCK_TTL must stay below "
                "CELERY_BROKER_VISIBILITY_TIMEOUT so a dead worker's lock "
                "expires before its task is redelivered."
            )
        return self

    @model_validator(mode="after")
    def _derive_keycloak_urls(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~141-159."""
        token_url = self.SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL
        if "/realms/" in token_url:
            server_default = token_url.split("/realms/")[0]
            realm_default = token_url.split("/realms/")[1].split("/")[0]
        else:
            server_default = "http://kc.odl.local:7080"
            realm_default = "ovs-local"

        self.KEYCLOAK_SERVER_URL = self.KEYCLOAK_SERVER_URL or server_default
        self.KEYCLOAK_REALM = self.KEYCLOAK_REALM or realm_default
        self.SOCIAL_AUTH_KEYCLOAK_LOGOUT_URL = (
            self.SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL.replace(
                "/protocol/openid-connect/auth", "/protocol/openid-connect/logout"
            )
        )
        return self

    @model_validator(mode="after")
    def _derive_static_and_cdn_urls(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~322-335 (STATIC_URL / AWS_S3_CUSTOM_DOMAIN /
        VIDEO_CLOUDFRONT_BASE_URL)."""
        self.VIDEO_CLOUDFRONT_BASE_URL = self.VIDEO_CLOUDFRONT_BASE_URL or (
            f"https://{self.VIDEO_CLOUDFRONT_DIST}.cloudfront.net/"
        )

        if self.CLOUDFRONT_DIST:
            self.STATIC_URL = urljoin(
                f"https://{self.CLOUDFRONT_DIST}.cloudfront.net", "/static/"
            )
            self.AWS_S3_CUSTOM_DOMAIN = f"{self.CLOUDFRONT_DIST}.cloudfront.net"
        else:
            self.STATIC_URL = "/static/"
            self.AWS_S3_CUSTOM_DOMAIN = None
        return self

    @model_validator(mode="after")
    def _alias_s3_bucket_name(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~408 (`VIDEO_S3_BUCKET =
        AWS_STORAGE_BUCKET_NAME = get_string(...)`)."""
        self.AWS_STORAGE_BUCKET_NAME = self.VIDEO_S3_BUCKET
        return self

    @model_validator(mode="after")
    def _scan_features(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~590-595 (dynamic FEATURE_* prefix scan)."""
        import os

        prefix = self.ODL_VIDEO_FEATURES_PREFIX
        self.FEATURES = {
            key[len(prefix) :]: get_any(key, None)
            for key in os.environ
            if key.startswith(prefix)
        }
        return self

    @model_validator(mode="after")
    def _derive_admins(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~293-297."""
        self.ADMINS = (("Admins", self.ADMIN_EMAIL),) if self.ADMIN_EMAIL else ()
        return self

    @model_validator(mode="after")
    def _derive_paths(self) -> AqueductSettings:
        """Recompute BASE_DIR-relative paths so they aren't frozen to the
        filesystem layout of the machine `generate_aqueduct_settings` ran on."""
        base_dir = self.BASE_DIR
        self.STATIC_ROOT = f"{base_dir}/staticfiles"
        self.STATICFILES_DIRS = (f"{base_dir}/static",)
        self.TEMPLATES[0]["DIRS"] = [f"{base_dir}/templates/"]
        self.WEBPACK_LOADER["DEFAULT"]["CACHE"] = not self.DEBUG
        self.WEBPACK_LOADER["DEFAULT"]["STATS_FILE"] = f"{base_dir}/webpack-stats.json"
        return self

    @model_validator(mode="after")
    def _derive_internal_ips(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~270 (`INTERNAL_IPS = (get_string("HOST_IP",
        "127.0.0.1"),)`)."""
        self.INTERNAL_IPS = (self.HOST_IP,)
        return self

    @model_validator(mode="after")
    def _derive_databases(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~221-235."""
        database_url = self.DATABASE_URL or f"sqlite:///{self.BASE_DIR}/db.sqlite3"
        config = dj_database_url.parse(database_url)
        config["CONN_MAX_AGE"] = self.ODL_VIDEO_DB_CONN_MAX_AGE
        config["OPTIONS"] = (
            {} if self.ODL_VIDEO_DB_DISABLE_SSL else {"sslmode": "require"}
        )
        self.DEFAULT_DATABASE_CONFIG = config
        self.DATABASES = {"default": config}
        return self

    @model_validator(mode="after")
    def _derive_celery_and_cache_settings(self) -> AqueductSettings:
        """Port of odl_video/settings.py ~499-541 (Redis/Celery URL chain and
        their downstream derived dicts)."""
        from redbeat import RedBeatScheduler

        self.CELERY_BEAT_SCHEDULER = RedBeatScheduler
        self.CELERY_BROKER_URL = self.CELERY_BROKER_URL or self.REDIS_URL
        self.CELERY_RESULT_BACKEND = self.REDIS_URL
        self.CELERY_REDBEAT_REDIS_URL = self.CELERY_BROKER_URL
        self.CELERY_REDIS_MAX_CONNECTIONS = self.REDIS_MAX_CONNECTIONS
        self.CELERY_BROKER_TRANSPORT_OPTIONS = {
            "visibility_timeout": self.CELERY_BROKER_VISIBILITY_TIMEOUT,
        }
        self.CACHES["redis"]["LOCATION"] = self.CELERY_BROKER_URL
        self.CACHES["redis"]["OPTIONS"]["CONNECTION_POOL_KWARGS"]["max_connections"] = (
            self.REDIS_MAX_CONNECTIONS
        )
        self.AWS_S3_UPLOAD_TRANSFER_CONFIG = {
            "multipart_threshold": self.AWS_S3_UPLOAD_MULTIPART_THRESHOLD_MB * self.MB,
            "multipart_chunksize": self.AWS_S3_UPLOAD_MULTIPART_CHUNKSIZE_MB * self.MB,
            "max_concurrency": self.AWS_S3_UPLOAD_MAX_CONCURRENCY,
            "num_download_attempts": self.AWS_S3_UPLOAD_NUM_DOWNLOAD_ATTEMPTS,
            "max_io_queue": self.AWS_S3_UPLOAD_MAX_IO_QUEUE,
            "io_chunksize": self.AWS_S3_UPLOAD_IO_CHUNKSIZE_KB * self.KB,
            "use_threads": self.AWS_S3_UPLOAD_USE_THREADS,
        }
        return self


class DevAqueductSettings(AqueductSettings):
    """Local-dev variant: fills missing values from Vault via OIDC instead of
    requiring a .env file.

    NOTE: `VAULT_AQUEDUCT_PATH` and the OIDC `role` default ("odl-video-service")
    below are placeholders — they need confirming against the live Vault
    instance (e.g. `vault kv list secret-odl-video-service/`) before this is
    used for real, since that isn't discoverable from this repo alone. Also
    note this app's Vault policy reportedly also grants broad
    `secret-operations/*` access; tightening that is an ol-infrastructure
    policy-hardening concern, out of scope for this settings-modeling change.
    """

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        from django_aqueduct.sources.vault import VaultSettingsSource
        import os

        return (
            init_settings,
            env_settings,
            VaultSettingsSource(
                settings_cls,
                vault_url=os.environ["VAULT_ADDR"],
                vault_path=os.environ.get("VAULT_AQUEDUCT_PATH", ""),
                mount_point="secret-odl-video-service",
                kv_version="2",
                auth_method="oidc",
                role=os.environ.get("VAULT_AQUEDUCT_ROLE", "odl-video-service"),
            ),
        )
