"""
Admin for UI app
"""

from django.contrib import admin
from ui import models


class ViewListsInline(admin.TabularInline):
    """Inline model for collection view_lists"""
    model = models.Collection.view_lists.through
    verbose_name = "View moira lists"
    verbose_name_plural = "View moira lists"


class AdminListsInline(admin.TabularInline):
    """Inline model for collection admin_lists"""
    model = models.Collection.admin_lists.through
    verbose_name = "Admin moira lists"
    verbose_name_plural = "Admin moira lists"


class CollectionAdmin(admin.ModelAdmin):
    """Customized collection admin model"""
    inlines = [
        ViewListsInline,
        AdminListsInline
    ]
    exclude = ('view_lists', 'admin_lists')

admin.site.register(models.Collection, CollectionAdmin)
admin.site.register(models.MoiraList)
admin.site.register(models.Video)
admin.site.register(models.VideoFile)
admin.site.register(models.VideoThumbnail)
