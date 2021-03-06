# Generated by Django 2.2.10 on 2020-04-30 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0028_add_edx_endpoint_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="is_logged_in_only",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="video",
            name="is_logged_in_only",
            field=models.BooleanField(default=False),
        ),
    ]
