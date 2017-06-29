"""
Admin for UI app
"""

from django.contrib import admin
from ui.models import MoiraList, Video, VideoFile

admin.site.register(MoiraList)
admin.site.register(Video)
admin.site.register(VideoFile)
