# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-08-01 16:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui', '0005_video_statuses'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='multiangle',
            field=models.BooleanField(default=False),
        ),
    ]