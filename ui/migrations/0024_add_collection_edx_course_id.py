# Generated by Django 2.1.7 on 2019-08-01 16:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0023_collection_allow_share_openedx"),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="edx_course_id",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
    ]
