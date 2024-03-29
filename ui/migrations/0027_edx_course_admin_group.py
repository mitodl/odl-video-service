# Generated by Django 2.1.11 on 2020-03-19 21:34

from django.contrib.auth.models import Group
from django.db import migrations

EDX_ADMIN_GROUP = "edX Course Admin"


def create_edx_course_admin_group(*args, **kwargs):
    """
    Ensures that an auth group exists for users that can edit edX course info
    """
    Group.objects.get_or_create(name=EDX_ADMIN_GROUP)


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0026_schedule_retranscode"),
    ]

    operations = [
        migrations.RunPython(create_edx_course_admin_group, migrations.RunPython.noop)
    ]
