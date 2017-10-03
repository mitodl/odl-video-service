from django.db import migrations, models


def forwards_func(apps, schema_editor):
    """
    It adds default email templates
    """
    NotificationEmail = apps.get_model("mail", "NotificationEmail")
    db_alias = schema_editor.connection.alias

    # first email for reminders to pay one week before deadline
    NotificationEmail.objects.using(db_alias).create(
        notification_type='Success',
        email_subject="Video {video_title} done processing",
        email_body="""Congratulations. Your video, [{video_title}]({video_url}) is done processing and is now available on the ODL video site.
You can view it and change settings at the following URL:

{video_url}
        """
    )

    # second email for reminders to pay 2 days before deadline
    NotificationEmail.objects.using(db_alias).create(
        notification_type='Invalid Input Error',
        email_subject="Error posting your video {video_title}",
        email_body="""We’re sorry, there was a problem processing your file: please check if the file you uploaded is an actual video and you can play it.
If you think it should work, please contact us at {support_email}

{video_url}
        """
    )

    # third email for reminders to pay on the day of deadline
    NotificationEmail.objects.using(db_alias).create(
        notification_type='Other Error',
        email_subject="Error posting your video {video_title}",
        email_body="""Sorry, there was a problem processing your file.
Someone on the engineering team has been notified and will contact you shortly.

{video_url}
        """
    )


def reverse_func(apps, schema_editor):
    """
    It deletes all the default email templates
    """
    NotificationEmail = apps.get_model("mail", "NotificationEmail")
    db_alias = schema_editor.connection.alias
    NotificationEmail.objects.using(db_alias).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
