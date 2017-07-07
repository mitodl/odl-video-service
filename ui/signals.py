"""
ui model signals
"""
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from ui.models import VideoFile, VideoThumbnail


@receiver(pre_delete, sender=VideoFile)
@receiver(pre_delete, sender=VideoThumbnail)
def delete_s3_files(sender, **kwargs):  # pylint:disable=unused-argument
    """
    Make sure S3 files are deleted along with associated video file/thumbnail object
    """
    kwargs['instance'].delete_from_s3()
