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
    search_fields = (
        'title',
        'slug',
        'view_lists__name',
        'admin_lists__name',
        'stream_source',
        'owner__username',
        'owner__email',
    )


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
    search_fields = (
        'title',
        'description',
        'source_url',
        'status',
        'collection__title',
        'view_lists__name',
        'encode_jobs__state',
    )


class VideoFileAdmin(admin.ModelAdmin):
    """Customized VideoFile admin model"""
    model = models.VideoFile
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    search_fields = ('encoding', 'bucket_name', 'video__titles', )


class YouTubeVideoAdmin(admin.ModelAdmin):
    """Customized YouTubeVideo admin model"""
    model = models.YouTubeVideo
    list_display = ('id', 'created_at', 'status', 'video_title', 'video_key',
                    'video_collection',)
    list_filter = ['status', 'video__collection']
    search_fields = ['id', 'video__key', 'video__title']

    def video_title(self, obj):
        """video_title"""
        return obj.video.title

    def video_key(self, obj):
        """video_key"""
        return obj.video.key

    def video_collection(self, obj):
        """video_collection"""
        return obj.video.collection.title

    def created_at(self, obj):
        """created_at"""
        return obj.created_at


class MoiraListAdmin(admin.ModelAdmin):
    """admin page of Moira list"""
    model = models.MoiraList
    list_display = ('name',)
    search_fields = ('name',)


class VideoSubtitleAdmin(admin.ModelAdmin):
    """admin page of Moira list"""
    model = models.VideoSubtitle
    list_display = ('filename', 'language', )
    search_fields = ('filename', 'language', 'bucket_name', 'video__titles', )


class VideoThumbnailAdmin(admin.ModelAdmin):
    """admin page of Moira list"""
    model = models.VideoThumbnail
    list_display = ('max_width', 'max_height', )
    search_fields = ('max_width', 'max_height', 'bucket_name', 'video__titles', )


admin.site.register(models.Collection, CollectionAdmin)
admin.site.register(models.MoiraList, MoiraListAdmin)
admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoFile, VideoFileAdmin)
admin.site.register(models.VideoThumbnail, VideoThumbnailAdmin)
admin.site.register(models.VideoSubtitle, VideoSubtitleAdmin)
admin.site.register(models.YouTubeVideo, YouTubeVideoAdmin)
