# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-08-21 21:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0008_video_statuses"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="collection",
            name="moira_lists",
        ),
        migrations.AddField(
            model_name="collection",
            name="admin_lists",
            field=models.ManyToManyField(
                blank=True, related_name="admin_lists", to="ui.MoiraList"
            ),
        ),
        migrations.AddField(
            model_name="collection",
            name="view_lists",
            field=models.ManyToManyField(
                blank=True, related_name="view_lists", to="ui.MoiraList"
            ),
        ),
        migrations.AlterField(
            model_name="moiralist",
            name="name",
            field=models.CharField(max_length=250, unique=True),
        ),
    ]
