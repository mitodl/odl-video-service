# Generated by Django 2.2.10 on 2020-04-17 17:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0004_add_timestamps'),
    ]

    operations = [
        migrations.DeleteModel(
            name='NotificationEmail',
        ),
    ]