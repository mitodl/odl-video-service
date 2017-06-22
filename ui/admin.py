"""
Admin for UI app
"""

from django.contrib import admin
from ui.models import MoiraList, Video

admin.site.register(MoiraList)
admin.site.register(Video)
