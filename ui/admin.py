"""
Admin for UI app
"""

from django.contrib import admin
from ui import models


admin.site.register(models.Collection)
admin.site.register(models.MoiraList)
admin.site.register(models.Video)
admin.site.register(models.VideoFile)
admin.site.register(models.VideoThumbnail)
