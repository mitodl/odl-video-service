# Generated by Django 1.10.5 on 2017-07-28 14:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0004_add_videothumbnail"),
    ]

    operations = [
        migrations.AlterField(
            model_name="video",
            name="status",
            field=models.TextField(
                choices=[
                    ("Created", "Created"),
                    ("Uploading", "Uploading"),
                    ("Upload failed", "Upload failed"),
                    ("Transcoding", "Transcoding"),
                    ("Transcode failed", "Transcode failed"),
                    ("Complete", "Complete"),
                    ("Error", "Error"),
                ],
                default="Created",
                max_length=30,
            ),
        ),
    ]
