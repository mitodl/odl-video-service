"""Models for techtv2ovs"""

from django.db import models
from django.db.models import IntegerField

from odl_video.models import TimestampedModel
from techtv2ovs.constants import ImportStatus
from ui.models import Collection, Video


class TechTVCollection(TimestampedModel):
    """
    A TechTV collection with only the most relevant fields.
    """

    id = IntegerField(primary_key=True)
    collection = models.ForeignKey(Collection, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)  # noqa: DJ001
    owner_email = models.EmailField(null=True)  # noqa: DJ001

    def __str__(self):
        return self.name


class TechTVVideo(TimestampedModel):
    """
    A TechTV video with only the most relevant fields, and statuses to monitor migration to OVS
    """  # noqa: E501

    ttv_id = IntegerField(null=False)
    ttv_collection = models.ForeignKey(
        TechTVCollection, on_delete=models.CASCADE, null=True, blank=True
    )
    external_id = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    title = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    description = models.TextField(blank=True, null=True)  # noqa: DJ001
    video = models.ForeignKey(Video, on_delete=models.SET_NULL, null=True, blank=True)
    private = models.BooleanField(default=False, null=False)
    private_token = models.CharField(max_length=48, null=True, blank=True)  # noqa: DJ001
    status = models.CharField(  # noqa: DJ001
        null=True,
        choices=[(status, status) for status in ImportStatus.ALL_STATUSES],
        max_length=50,
    )
    videofile_status = models.CharField(  # noqa: DJ001
        null=True,
        choices=[(status, status) for status in ImportStatus.ALL_STATUSES],
        max_length=50,
    )
    thumbnail_status = models.CharField(  # noqa: DJ001
        null=True,
        choices=[(status, status) for status in ImportStatus.ALL_STATUSES],
        max_length=50,
    )
    subtitle_status = models.CharField(  # noqa: DJ001
        null=True,
        choices=[(status, status) for status in ImportStatus.ALL_STATUSES],
        max_length=50,
    )
    errors = models.TextField()
