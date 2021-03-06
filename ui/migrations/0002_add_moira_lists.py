# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-25 18:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MoiraList",
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
                ("name", models.CharField(max_length=250)),
            ],
        ),
        migrations.AddField(
            model_name="video",
            name="moira_lists",
            field=models.ManyToManyField(to="ui.MoiraList"),
        ),
    ]
