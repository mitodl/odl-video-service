"""Custom exceptions"""


class MoiraException(Exception):
    """Custom exception to be used when something goes wrong with Moira API calls"""


class GoogleAnalyticsException(Exception):
    """Custom exception to be used when something goes wrong with GA API calls"""


class KeycloakException(Exception):
    """Custom exception to be used when something goes wrong with Keycloak API calls"""
