"""
Models for the mail app
"""
from django.db import models


class NotificationEmail(models.Model):
    """
    Stores information for a notification email
    """
    SUCCESS = 'Success'
    INVALID_INPUT_ERROR = 'Invalid Input Error'
    OTHER_ERROR = 'Other Error'

    notification_type = models.CharField(
        null=False,
        default=SUCCESS,
        choices=[(status, status) for status in [SUCCESS, INVALID_INPUT_ERROR, OTHER_ERROR]],
        max_length=50,
        unique=True,
    )
    email_subject = models.TextField(null=False, blank=True)
    email_body = models.TextField(null=False, blank=True)

    def __str__(self):
        """String representation of NotificationEmail"""
        return "NotificationEmail notification_type={}".format(self.notification_type)
