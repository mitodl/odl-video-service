"""
Django App
"""
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

# pylint:disable=import-outside-toplevel


class UIConfig(AppConfig):
    """AppConfig for ui"""

    name = "ui"

    def ready(self):
        # check for missing configurations
        from django.conf import settings

        import ui.signals  # pylint:disable=unused-import

        missing_settings = []
        for setting_name in settings.MANDATORY_SETTINGS:
            if getattr(settings, setting_name, None) in (
                None,
                "",
            ):
                missing_settings.append(setting_name)
        if missing_settings:
            raise ImproperlyConfigured(
                "The following settings are missing: {}".format(
                    ", ".join(missing_settings)
                )
            )

        # write the x509 certification & key to files
        from ui.utils import write_x509_files

        write_x509_files()
