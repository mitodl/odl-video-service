# Generated by Django 1.10.5 on 2017-11-15 13:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0014_video_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="YouTubeVideo",
            fields=[
                (
                    "video",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to="ui.Video",
                    ),
                ),
                ("id", models.CharField(max_length=11, null=True)),
                ("status", models.CharField(default="uploading", max_length=24)),
            ],
        ),
    ]
