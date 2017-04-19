from django.conf import settings


def secrets(request):
    """
    Add secrets to the template context.
    """
    return {
        "DROPBOX_APP_KEY": settings.DROPBOX_APP_KEY,
        "DROPBOX_APP_SECRET": settings.DROPBOX_APP_SECRET,
    }
