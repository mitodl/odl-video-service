# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-09-01 18:43
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0009_moira_lists"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="video",
            options={"ordering": ["-created_at"]},
        ),
    ]
