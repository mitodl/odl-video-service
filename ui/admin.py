"""
Admin for UI app
"""
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from dj_elastictranscoder.models import EncodeJob
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
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


class VideoFilesInline(admin.TabularInline):
    """Inline model for video files"""
    model = models.VideoFile
    extra = 0
    readonly_fields = ['created_at']


class VideoSubtitlesInline(admin.TabularInline):
    """Inline model for video videoSubtitles"""
    model = models.VideoSubtitle
    extra = 0
    readonly_fields = ['created_at']


class VideoThumbnailsInline(admin.TabularInline):
    """Inline model for video thumbnails"""
    model = models.VideoThumbnail
    extra = 0
    readonly_fields = ['created_at']


class VideoEncodeJobsInline(GenericTabularInline):
    """
    Inline model for video encode job
    """
    model = EncodeJob
    extra = 0
    list_display = ('id', 'state', 'message')
    readonly_fields = ('id', 'state', 'message')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False


class VideoAdmin(admin.ModelAdmin):
    """Customized Video admin model"""
    model = models.Video
    inlines = [
        VideoEncodeJobsInline,
        VideoFilesInline,
        VideoSubtitlesInline,
        VideoThumbnailsInline
    ]
    list_display = (
        'title',
        'created_at'
    )
    list_filter = ['status']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


class VideoFileAdmin(admin.ModelAdmin):
    """Customized VideoFile admin model"""
    model = models.VideoFile
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


admin.site.register(models.Collection, CollectionAdmin)
admin.site.register(models.MoiraList)
admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoFile, VideoFileAdmin)
admin.site.register(models.VideoThumbnail)
admin.site.register(models.VideoSubtitle)
admin.site.register(models.YouTubeVideo)
