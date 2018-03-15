"""
Django settings for odl_video.
"""
import logging
import os
import platform
from urllib.parse import urljoin

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from odl_video.envs import (
    get_any,
    get_bool,
    get_int,
    get_key,
    get_string,
    parse_env
)

VERSION = "0.14.1"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parse_env(f'{BASE_DIR}/.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_string('SECRET_KEY', None)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_bool('DEBUG', False)

ALLOWED_HOSTS = ['*']

SECURE_SSL_REDIRECT = get_bool('ODL_VIDEO_SECURE_SSL_REDIRECT', True)


WEBPACK_LOADER = {
    'DEFAULT': {
        'CACHE': not DEBUG,
        'BUNDLE_DIR_NAME': 'bundles/',
        'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json'),
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [
            r'.+\.hot-update\.+',
            r'.+\.js\.map'
        ]
    }
}


# Application definition

INSTALLED_APPS = [
    'ui.apps.UIConfig',
    'cloudsync.apps.CloudSyncConfig',
    'techtv2ovs',
    'mail.apps.MailConfig',
    'dj_elastictranscoder',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'server_status',
    'raven.contrib.django.raven_compat',
]

DISABLE_WEBPACK_LOADER_STATS = get_bool("DISABLE_WEBPACK_LOADER_STATS", False)
if not DISABLE_WEBPACK_LOADER_STATS:
    INSTALLED_APPS += ('webpack_loader',)

MIDDLEWARE_CLASSES = [
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# enable the nplusone profiler only in debug mode
if DEBUG:
    INSTALLED_APPS += (
        'nplusone.ext.django',
    )
    MIDDLEWARE_CLASSES += (
        'nplusone.ext.django.NPlusOneMiddleware',
    )

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

LOGIN_REDIRECT_URL = "/"
if get_bool('USE_SHIBBOLETH', False):
    # TOUCHSTONE
    MIDDLEWARE_CLASSES.append('shibboleth.middleware.ShibbolethRemoteUserMiddleware')
    SHIBBOLETH_ATTRIBUTE_MAP = {
        "EPPN": (True, "username"),
        "MAIL": (True, "email"),
        # full name is in the "DISPLAY_NAME" header,
        # but no way to parse that into first_name and last_name...
    }
    AUTHENTICATION_BACKENDS = [
        'shibboleth.backends.ShibbolethRemoteUserBackend',
    ]
    LOGIN_URL = "/collections/"
else:
    LOGIN_URL = "/admin/login/"


ROOT_URLCONF = 'odl_video.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR + '/templates/'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'odl_video.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
# Uses DATABASE_URL to configure with sqlite default:
# For URL structure:
# https://github.com/kennethreitz/dj-database-url
DEFAULT_DATABASE_CONFIG = dj_database_url.parse(
    get_string(
        'DATABASE_URL',
        'sqlite:///{0}'.format(os.path.join(BASE_DIR, 'db.sqlite3'))
    )
)
DEFAULT_DATABASE_CONFIG['CONN_MAX_AGE'] = get_int('ODL_VIDEO_DB_CONN_MAX_AGE', 0)

if get_bool('ODL_VIDEO_DB_DISABLE_SSL', False):
    DEFAULT_DATABASE_CONFIG['OPTIONS'] = {}
else:
    DEFAULT_DATABASE_CONFIG['OPTIONS'] = {'sslmode': 'require'}

DATABASES = {
    'default': DEFAULT_DATABASE_CONFIG
}

# the full URL of the current application is mandatory
ODL_VIDEO_BASE_URL = get_string('ODL_VIDEO_BASE_URL', None)


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# Request files from the webpack dev server
USE_WEBPACK_DEV_SERVER = get_bool('ODL_VIDEO_USE_WEBPACK_DEV_SERVER', False)
WEBPACK_DEV_SERVER_HOST = get_string('WEBPACK_DEV_SERVER_HOST', '')
WEBPACK_DEV_SERVER_PORT = get_int('WEBPACK_DEV_SERVER_PORT', 8082)

# Important to define this so DEBUG works properly
INTERNAL_IPS = (get_string('HOST_IP', '127.0.0.1'), )

# Configure e-mail settings
EMAIL_BACKEND = get_string('ODL_VIDEO_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = get_string('ODL_VIDEO_EMAIL_HOST', 'localhost')
EMAIL_PORT = get_int('ODL_VIDEO_EMAIL_PORT', 25)
EMAIL_HOST_USER = get_string('ODL_VIDEO_EMAIL_USER', '')
EMAIL_HOST_PASSWORD = get_string('ODL_VIDEO_EMAIL_PASSWORD', '')
EMAIL_USE_TLS = get_bool('ODL_VIDEO_EMAIL_TLS', False)
EMAIL_SUPPORT = get_string('ODL_VIDEO_SUPPORT_EMAIL', 'support@example.com')
DEFAULT_FROM_EMAIL = get_string('ODL_VIDEO_FROM_EMAIL', 'webmaster@localhost')

MAILGUN_URL = get_string('MAILGUN_URL', None)
MAILGUN_KEY = get_string('MAILGUN_KEY', None)
MAILGUN_BATCH_CHUNK_SIZE = get_int('MAILGUN_BATCH_CHUNK_SIZE', 1000)
MAILGUN_RECIPIENT_OVERRIDE = get_string('MAILGUN_RECIPIENT_OVERRIDE', None)
MAILGUN_FROM_EMAIL = get_string('MAILGUN_FROM_EMAIL', 'no-reply@example.com')
MAILGUN_BCC_TO_EMAIL = get_string('MAILGUN_BCC_TO_EMAIL', 'no-reply@example.com')


# e-mail configurable admins
ADMIN_EMAIL = get_string('ODL_VIDEO_ADMIN_EMAIL', '')
if ADMIN_EMAIL != '':
    ADMINS = (('Admins', ADMIN_EMAIL),)
else:
    ADMINS = ()

# Logging configuration
LOG_LEVEL = get_string('ODL_VIDEO_LOG_LEVEL', 'INFO')
DJANGO_LOG_LEVEL = get_string('DJANGO_LOG_LEVEL', 'INFO')
SENTRY_LOG_LEVEL = get_string('SENTRY_LOG_LEVEL', 'ERROR')

# For logging to a remote syslog host
LOG_HOST = get_string('ODL_VIDEO_LOG_HOST', 'localhost')
LOG_HOST_PORT = get_int('ODL_VIDEO_LOG_HOST_PORT', 514)

HOSTNAME = platform.node().split('.')[0]

# nplusone profiler logger configuration
NPLUSONE_LOGGER = logging.getLogger('nplusone')
NPLUSONE_LOG_LEVEL = logging.ERROR

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        }
    },
    'formatters': {
        'verbose': {
            'format': (
                '[%(asctime)s] %(levelname)s %(process)d [%(name)s] '
                '%(filename)s:%(lineno)d - '
                '[{hostname}] - %(message)s'
            ).format(hostname=HOSTNAME),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'syslog': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.SysLogHandler',
            'facility': 'local7',
            'formatter': 'verbose',
            'address': (LOG_HOST, LOG_HOST_PORT)
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'sentry': {
            'level': SENTRY_LOG_LEVEL,
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'propagate': True,
            'level': DJANGO_LOG_LEVEL,
            'handlers': ['console', 'syslog'],
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': True,
        },
        'raven': {
            'level': SENTRY_LOG_LEVEL,
            'handlers': []
        },
        'nplusone': {
            'handlers': ['console'],
            'level': 'ERROR',
        }
    },
    'root': {
        'handlers': ['console', 'syslog'],
        'level': LOG_LEVEL,
    },
}

# to run the app locally on mac you need to bypass syslog
if get_bool('ODL_VIDEO_BYPASS_SYSLOG', False):
    LOGGING['handlers'].pop('syslog')
    LOGGING['loggers']['root']['handlers'] = ['console']
    LOGGING['loggers']['ui']['handlers'] = ['console']
    LOGGING['loggers']['django']['handlers'] = ['console']

# Sentry
ENVIRONMENT = get_string('ODL_VIDEO_ENVIRONMENT', 'dev')
SENTRY_CLIENT = 'raven.contrib.django.raven_compat.DjangoClient'
RAVEN_CONFIG = {
    'dsn': get_string('SENTRY_DSN', ''),
    'environment': ENVIRONMENT,
    'release': VERSION
}

# MIT keys
MIT_WS_CERTIFICATE = get_key('MIT_WS_CERTIFICATE', '')
MIT_WS_PRIVATE_KEY = get_key('MIT_WS_PRIVATE_KEY', '')

# x509 filenames
MIT_WS_CERTIFICATE_FILE = os.path.join(BASE_DIR, STATIC_ROOT, 'mit_x509.cert')
MIT_WS_PRIVATE_KEY_FILE = os.path.join(BASE_DIR, STATIC_ROOT, 'mit_x509.key')

# Dropbox key
DROPBOX_KEY = get_string('DROPBOX_KEY', '')

# AWS S3 upload settings
# the defaults values come from the default configuration in boto3.s3.transfer.TransferConfig
# apart from the first 2
KB = 1024
MB = KB * KB

# AWS
CLOUDFRONT_PRIVATE_KEY = get_key('CLOUDFRONT_PRIVATE_KEY', '')
CLOUDFRONT_KEY_ID = get_string('CLOUDFRONT_KEY_ID', '')
VIDEO_CLOUDFRONT_DIST = get_string('VIDEO_CLOUDFRONT_DIST', '')
VIDEO_CLOUDFRONT_BASE_URL = get_string(
    'VIDEO_CLOUDFRONT_BASE_URL',
    'https://{}.cloudfront.net/'.format(VIDEO_CLOUDFRONT_DIST)
)

CLOUDFRONT_DIST = get_string('STATIC_CLOUDFRONT_DIST', None)
if CLOUDFRONT_DIST:
    STATIC_URL = urljoin('https://{dist}.cloudfront.net'.format(dist=CLOUDFRONT_DIST), STATIC_URL)
    AWS_S3_CUSTOM_DOMAIN = '{dist}.cloudfront.net'.format(dist=CLOUDFRONT_DIST)

AWS_ACCESS_KEY_ID = get_string('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = get_string('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION = get_string('AWS_REGION', '')
AWS_S3_DOMAIN = get_string('AWS_S3_DOMAIN', 's3.amazonaws.com')

AWS_S3_UPLOAD_MULTIPART_THRESHOLD_MB = get_int('AWS_S3_UPLOAD_MULTIPART_THRESHOLD_MB', 32)
AWS_S3_UPLOAD_MULTIPART_CHUNKSIZE_MB = get_int('AWS_S3_UPLOAD_MULTIPART_CHUNKSIZE_MB', 32)
AWS_S3_UPLOAD_MAX_CONCURRENCY = get_int('AWS_S3_UPLOAD_MAX_CONCURRENCY', 10)
AWS_S3_UPLOAD_NUM_DOWNLOAD_ATTEMPTS = get_int('AWS_S3_UPLOAD_NUM_DOWNLOAD_ATTEMPTS', 5)
AWS_S3_UPLOAD_MAX_IO_QUEUE = get_int('AWS_S3_UPLOAD_MAX_IO_QUEUE', 100)
AWS_S3_UPLOAD_IO_CHUNKSIZE_KB = get_int('AWS_S3_UPLOAD_IO_CHUNKSIZE_KB', 256)
AWS_S3_UPLOAD_USE_THREADS = get_bool('AWS_S3_UPLOAD_USE_THREADS', True)

AWS_S3_UPLOAD_TRANSFER_CONFIG = dict(
    multipart_threshold=AWS_S3_UPLOAD_MULTIPART_THRESHOLD_MB * MB,
    multipart_chunksize=AWS_S3_UPLOAD_MULTIPART_CHUNKSIZE_MB * MB,
    max_concurrency=AWS_S3_UPLOAD_MAX_CONCURRENCY,
    num_download_attempts=AWS_S3_UPLOAD_NUM_DOWNLOAD_ATTEMPTS,
    max_io_queue=AWS_S3_UPLOAD_MAX_IO_QUEUE,
    io_chunksize=AWS_S3_UPLOAD_IO_CHUNKSIZE_KB * KB,
    use_threads=AWS_S3_UPLOAD_USE_THREADS
)

# AWS ElasticTranscoder
ET_PIPELINE_ID = get_string('ET_PIPELINE_ID', '')
ET_PRESET_IDS = get_string(
    'ET_PRESET_IDS',
    '1351620000001-200010,1351620000001-200020,1351620000001-200050'
).split(',')

if ET_PRESET_IDS == ['']:  # This may happen if `ET_PRESET_IDS=` is in .env file.
    raise ImproperlyConfigured('ET_PRESET_IDS cannot be blank, please check your settings & environment')

VIDEO_CLOUDFRONT_DIST = get_string('VIDEO_CLOUDFRONT_DIST', '')
VIDEO_S3_BUCKET = get_string('VIDEO_S3_BUCKET', '')
VIDEO_S3_TRANSCODE_BUCKET = get_string('VIDEO_S3_TRANSCODE_BUCKET', '')
VIDEO_S3_THUMBNAIL_BUCKET = get_string('VIDEO_S3_THUMBNAIL_BUCKET', '')
VIDEO_S3_SUBTITLE_BUCKET = get_string('VIDEO_S3_SUBTITLE_BUCKET', '')
VIDEO_S3_WATCH_BUCKET = get_string('VIDEO_S3_WATCH_BUCKET', '')

# server-status
STATUS_TOKEN = get_string("STATUS_TOKEN", "")
HEALTH_CHECK = ['CELERY', 'REDIS', 'POSTGRES']

ADWORDS_CONVERSION_ID = get_string("ADWORDS_CONVERSION_ID", "")
GA_TRACKING_ID = get_string("GA_TRACKING_ID", "")
GA_DIMENSION_CAMERA = get_string("GA_DIMENSION_CAMERA", "")
REACT_GA_DEBUG = get_bool("REACT_GA_DEBUG", False)

YT_CLIENT_ID = get_string('YT_CLIENT_ID', '')
YT_PROJECT_ID = get_string('YT_PROJECT_ID', '')
YT_CLIENT_SECRET = get_string('YT_CLIENT_SECRET', '')
YT_ACCESS_TOKEN = get_string('YT_ACCESS_TOKEN', '')
YT_REFRESH_TOKEN = get_string('YT_REFRESH_TOKEN', '')

LECTURE_CAPTURE_USER = get_string('LECTURE_CAPTURE_USER', '')

ENABLE_VIDEO_PERMISSIONS = get_bool('ENABLE_VIDEO_PERMISSIONS', False)

# List of mandatory settings. If any of these is not set, the app will not start
# and will raise an ImproperlyConfigured exception
MANDATORY_SETTINGS = [
    'AWS_ACCESS_KEY_ID',
    'AWS_REGION',
    'AWS_S3_DOMAIN',
    'AWS_SECRET_ACCESS_KEY',
    'CLOUDFRONT_KEY_ID',
    'CLOUDFRONT_PRIVATE_KEY',
    'DROPBOX_KEY',
    'ET_PIPELINE_ID',
    'LECTURE_CAPTURE_USER',
    'MAILGUN_KEY',
    'MAILGUN_URL',
    'ODL_VIDEO_BASE_URL',
    'REDIS_URL',
    'SECRET_KEY',
    'VIDEO_CLOUDFRONT_DIST',
    'LECTURE_CAPTURE_USER',
    'MIT_WS_CERTIFICATE',
    'MIT_WS_PRIVATE_KEY',
    'VIDEO_S3_BUCKET',
    'VIDEO_S3_TRANSCODE_BUCKET',
    'VIDEO_S3_THUMBNAIL_BUCKET',
    'VIDEO_S3_SUBTITLE_BUCKET',
    'VIDEO_S3_WATCH_BUCKET',
    'ENABLE_VIDEO_PERMISSIONS',
]

if ENABLE_VIDEO_PERMISSIONS:
    MANDATORY_SETTINGS += [
        'YT_ACCESS_TOKEN',
        'YT_REFRESH_TOKEN',
        'YT_CLIENT_ID',
        'YT_CLIENT_SECRET',
        'YT_PROJECT_ID',
    ]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    )
}

# Celery
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
REDIS_URL = get_string("REDIS_URL", None)
USE_CELERY = True
CELERY_BROKER_URL = get_string("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = REDIS_URL

CELERY_TASK_ALWAYS_EAGER = get_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = get_bool("CELERY_TASK_EAGER_PROPAGATES", True)

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULE = {
    'update-statuses': {
        'task': 'cloudsync.tasks.update_video_statuses',
        'schedule': get_int('VIDEO_STATUS_UPDATE_FREQUENCY', 60)
    },
    'update-youtube-statuses': {
        'task': 'cloudsync.tasks.update_youtube_statuses',
        'schedule': get_int('VIDEO_STATUS_UPDATE_FREQUENCY', 60)
    },
    'watch-bucket': {
        'task': 'cloudsync.tasks.monitor_watch_bucket',
        'schedule': get_int('VIDEO_WATCH_BUCKET_FREQUENCY', 900)
    }
}

# django cache back-ends
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'local-in-memory-cache',
    },
    'redis': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
    },
}


# features flags
def get_all_config_keys():
    """Returns all the configuration keys from both environment and configuration files"""
    return list(os.environ.keys())


ODL_VIDEO_FEATURES_PREFIX = get_string('ODL_VIDEO_FEATURES_PREFIX', 'FEATURE_')
FEATURES = {
    key[len(ODL_VIDEO_FEATURES_PREFIX):]: get_any(key, None) for key
    in get_all_config_keys() if key.startswith(ODL_VIDEO_FEATURES_PREFIX)
}

MIDDLEWARE_FEATURE_FLAG_QS_PREFIX = get_string("MIDDLEWARE_FEATURE_FLAG_QS_PREFIX", None)
MIDDLEWARE_FEATURE_FLAG_COOKIE_NAME = get_string(
    'MIDDLEWARE_FEATURE_FLAG_COOKIE_NAME', 'ODL_VIDEO_FEATURE_FLAGS')
MIDDLEWARE_FEATURE_FLAG_COOKIE_MAX_AGE_SECONDS = get_int(
    'MIDDLEWARE_FEATURE_FLAG_COOKIE_MAX_AGE_SECONDS', 60 * 60)

if MIDDLEWARE_FEATURE_FLAG_QS_PREFIX:
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
        'odl_video.middleware.QueryStringFeatureFlagMiddleware',
        'odl_video.middleware.CookieFeatureFlagMiddleware',
    )
