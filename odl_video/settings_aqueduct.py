"""Opt-in django-aqueduct settings module.

Select this module by setting `DJANGO_SETTINGS_MODULE=odl_video.settings_aqueduct`.
`odl_video.settings` (the default) is untouched and continues to work exactly
as before — this is a parallel, opt-in entry point, not a replacement.

See `odl_video/aqueduct_settings.py` for the underlying Pydantic model.
"""

from mitol.common.envs import import_settings_modules

from django_aqueduct import configure_django_settings
from odl_video.aqueduct_settings import AqueductSettings
from odl_video.envs import get_string
from odl_video.sentry import init_sentry

VERSION = "0.94.1"

# Initialize Sentry before doing anything else, mirroring the import-time
# side effect at the top of odl_video/settings.py, so config errors raised
# while building AqueductSettings (e.g. a missing required field) are still
# captured.
init_sentry(
    dsn=get_string("SENTRY_DSN", ""),
    environment=get_string("ODL_VIDEO_ENVIRONMENT", "dev"),
    version=VERSION,
    log_level=get_string("SENTRY_LOG_LEVEL", "ERROR"),
)

configure_django_settings(AqueductSettings)

# LOGGING is deliberately not a field on AqueductSettings (see the module
# docstring in aqueduct_settings.py) — it's built by a factory that reads
# django.conf.settings.DEBUG at logging-configuration time. Import it the
# same way odl_video/settings.py does.
import_settings_modules("mitol.observability.settings.logging")
