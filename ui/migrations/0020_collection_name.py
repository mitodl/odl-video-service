# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-05-02 18:52
from __future__ import unicode_literals

from django.db import migrations, models


def forwards_func(apps, schema_editor):
    Collection = apps.get_model("ui", "Collection")
    for collection in Collection.objects.filter(
        techtvcollection__isnull=True
    ).iterator():
        collection.slug = collection.title
        collection.save()


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0019_add_timestamps"),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="slug",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(forwards_func, reverse_func),
    ]
