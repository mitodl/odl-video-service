# Generated by Django 1.10.5 on 2018-03-01 18:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0015_youtubevideo"),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="stream_source",
            field=models.CharField(
                blank=True,
                choices=[("Youtube", "Youtube"), ("Cloudfront", "Cloudfront")],
                max_length=10,
                null=True,
            ),
        ),
    ]
