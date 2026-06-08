from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.utils import timezone

from ui.constants import VideoStatus


def fail_stuck_uploading_videos(apps, schema_editor):
    """Fail videos stuck in UPLOADING past the configured threshold."""
    Video = apps.get_model("ui", "Video")
    threshold = timezone.now() - timedelta(
        hours=settings.STUCK_UPLOADING_THRESHOLD_HOURS
    )
    Video.objects.filter(
        status=VideoStatus.UPLOADING, updated_at__lt=threshold
    ).update(status=VideoStatus.UPLOAD_FAILED)


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0042_alter_videothumbnail_options"),
    ]

    operations = [
        migrations.RunPython(
            fail_stuck_uploading_videos, migrations.RunPython.noop
        ),
    ]
