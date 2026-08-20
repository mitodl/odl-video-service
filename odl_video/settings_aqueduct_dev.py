"""Opt-in django-aqueduct settings module for local dev, backed by Vault.

Select this module by setting
`DJANGO_SETTINGS_MODULE=odl_video.settings_aqueduct_dev`. Missing values are
filled in from Vault — configured entirely via `VAULT_*` environment
variables (`VAULT_ADDR`, `VAULT_PATH`, `VAULT_MOUNT`, `VAULT_AUTH_METHOD`,
`VAULT_ROLE`, ...) — instead of requiring a local `.env` file. When
`VAULT_ADDR` is unset it degrades gracefully to plain environment settings.
`odl_video.settings` (the default) is untouched.

See `odl_video/aqueduct_settings.py` for the underlying Pydantic model
(`DevAqueductSettings`) and `django_aqueduct.sources.dev` for the Vault
source wiring.
"""

from mitol.common.envs import import_settings_modules

from django_aqueduct import configure_django_settings
from odl_video.aqueduct_settings import DevAqueductSettings
from odl_video.sentry import init_sentry


def _init_sentry(model):
    """Initialize Sentry from the validated model, before Django settings exist.

    Runs as the `pre_configure` hook: after the model has validated (so the
    values are typed and may have arrived via the Vault source, which the
    legacy env-reading helpers could not see) but before the values are
    injected into this module — mirroring the import-time Sentry init at the
    top of odl_video/settings.py. Note that an error raised while *building*
    the model (e.g. a missing required field) surfaces on stderr rather than
    in Sentry, since the model must exist before this hook can run.
    """
    init_sentry(
        dsn=model.SENTRY_DSN,
        environment=model.ENVIRONMENT,
        version=model.VERSION,
        log_level=model.SENTRY_LOG_LEVEL,
    )


configure_django_settings(DevAqueductSettings, pre_configure=_init_sentry)

# LOGGING is deliberately not a field on AqueductSettings (see the module
# comments in aqueduct_settings.py) — it's built by a factory that reads
# django.conf.settings.DEBUG at logging-configuration time. Import it the
# same way odl_video/settings.py does.
import_settings_modules("mitol.observability.settings.logging")
