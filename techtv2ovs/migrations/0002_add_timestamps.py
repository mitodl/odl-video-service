# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-05-02 18:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('techtv2ovs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='techtvcollection',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='techtvcollection',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='techtvvideo',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='techtvvideo',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
