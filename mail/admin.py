"""
Admin views for mail
"""

from django.contrib import admin

from mail.models import NotificationEmail


class NotificationEmailAdmin(admin.ModelAdmin):
    """Admin for AutomaticReminderEmail"""
    model = NotificationEmail
    list_display = ('notification_type', )
    search_fields = ('notification_type', 'email_subject', )


admin.site.register(NotificationEmail, NotificationEmailAdmin)
