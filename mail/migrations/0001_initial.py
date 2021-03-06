# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-08-15 19:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NotificationEmail",
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
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("Success", "Success"),
                            ("Invalid Input Error", "Invalid Input Error"),
                            ("Other Error", "Other Error"),
                        ],
                        default="Success",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("email_subject", models.TextField(blank=True)),
                ("email_body", models.TextField(blank=True)),
            ],
        ),
    ]
