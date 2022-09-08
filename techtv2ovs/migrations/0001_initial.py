# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2018-02-02 16:39
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("ui", "0015_youtubevideo"),
    ]

    operations = [
        migrations.CreateModel(
            name="TechTVCollection",
            fields=[
                ("id", models.IntegerField(primary_key=True, serialize=False)),
                ("name", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("owner_email", models.EmailField(max_length=254, null=True)),
                (
                    "collection",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="ui.Collection",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TechTVVideo",
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
                ("ttv_id", models.IntegerField()),
                (
                    "external_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("title", models.CharField(blank=True, max_length=255, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("private", models.BooleanField(default=False)),
                (
                    "private_token",
                    models.CharField(blank=True, max_length=48, null=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Created", "Created"),
                            ("Complete", "Complete"),
                            ("Error", "Error"),
                            ("Missing", "Missing"),
                        ],
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "videofile_status",
                    models.CharField(
                        choices=[
                            ("Created", "Created"),
                            ("Complete", "Complete"),
                            ("Error", "Error"),
                            ("Missing", "Missing"),
                        ],
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "thumbnail_status",
                    models.CharField(
                        choices=[
                            ("Created", "Created"),
                            ("Complete", "Complete"),
                            ("Error", "Error"),
                            ("Missing", "Missing"),
                        ],
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "subtitle_status",
                    models.CharField(
                        choices=[
                            ("Created", "Created"),
                            ("Complete", "Complete"),
                            ("Error", "Error"),
                            ("Missing", "Missing"),
                        ],
                        max_length=50,
                        null=True,
                    ),
                ),
                ("errors", models.TextField()),
                (
                    "ttv_collection",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="techtv2ovs.TechTVCollection",
                    ),
                ),
                (
                    "video",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="ui.Video",
                    ),
                ),
            ],
        ),
    ]
