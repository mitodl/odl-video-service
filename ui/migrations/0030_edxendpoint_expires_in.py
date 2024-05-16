# Generated by Django 2.2.13 on 2021-02-08 23:02

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0029_logged_in_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="edxendpoint",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="edxendpoint",
            name="expires_in",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="edxendpoint",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
