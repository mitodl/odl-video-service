"""
Django App
"""
from django.apps import AppConfig


class UIConfig(AppConfig):
    """AppConfig for ui"""
    name = 'ui'

    def ready(self):
        import ui.signals  # pylint:disable=unused-variable
