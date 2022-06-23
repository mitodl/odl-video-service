# Generated by Django 2.2.13 on 2021-10-21 19:02

from django.db import migrations, models
from encrypted_model_fields.fields import EncryptedCharField


def assign_collection_endpoints_from_global_default(apps, schema_editor):
    """
    If a default endpoint exists, assign that explicitly to configured collections and then remove it as the default
    """
    EdxEndpoint = apps.get_model("ui", "EdxEndpoint")
    Collection = apps.get_model("ui", "Collection")

    default_endpoint = EdxEndpoint.objects.filter(is_global_default=True).first()

    if not default_endpoint:
        return

    # add the default_endpoint as one of the configured edx_endpoints
    for collection in Collection.objects.filter(edx_course_id__isnull=False):
        collection.edx_endpoints.add(default_endpoint)

    default_endpoint.is_global_default = False
    default_endpoint.save()


def set_client_id_and_secret_key(apps, schema_editor):
    """Update existing endpoints to use the client id and secret key from settings"""
    from django.conf import settings

    EdxEndpoint = apps.get_model("ui", "EdxEndpoint")
    EdxEndpoint.objects.update(
        client_id=settings.OPENEDX_API_CLIENT_ID,
        secret_key=settings.OPENEDX_API_CLIENT_SECRET,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ui", "0030_edxendpoint_expires_in"),
    ]

    operations = [
        migrations.RunPython(
            assign_collection_endpoints_from_global_default, migrations.RunPython.noop
        ),
        migrations.AddField(
            model_name="edxendpoint",
            name="client_id",
            field=models.CharField(max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="edxendpoint",
            name="secret_key",
            field=models.CharField(max_length=512, null=True),
        ),
        migrations.RunPython(set_client_id_and_secret_key, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="edxendpoint",
            name="client_id",
            field=EncryptedCharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="edxendpoint",
            name="secret_key",
            field=EncryptedCharField(max_length=100),
        ),
    ]