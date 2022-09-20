# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-27 19:42
from __future__ import unicode_literals

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0002_add_moira_lists"),
    ]

    operations = [
        migrations.CreateModel(
            name="VideoFile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("s3_object_key", models.TextField(unique=True)),
                ("bucket_name", models.CharField(max_length=63)),
                ("encoding", models.CharField(default="original", max_length=128)),
                ("preset_id", models.CharField(blank=True, max_length=128, null=True)),
            ],
        ),
        migrations.RemoveField(
            model_name="video",
            name="s3_object_key",
        ),
        migrations.AddField(
            model_name="video",
            name="s3_subkey",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        migrations.AddField(
            model_name="video",
            name="status",
            field=models.TextField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="videofile",
            name="video",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="ui.Video"
            ),
        ),
    ]
