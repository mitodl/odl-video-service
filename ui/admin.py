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


class EdxEndpointAdmin(admin.ModelAdmin):
    """EdxEndpoint admin"""
    model = models.EdxEndpoint
    list_display = ('id', 'name', 'base_url', 'is_global_default')
    ordering = ['-is_global_default', 'id']


class CollectionEdxEndpointInlineAdmin(admin.StackedInline):
    """CollectionEdxEndpoint inline admin"""
    model = models.CollectionEdxEndpoint
    extra = 1


class CollectionAdmin(admin.ModelAdmin):
    """Customized collection admin model"""
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    list_filter = ['stream_source']
    autocomplete_fields = ['owner', 'view_lists', 'admin_lists']
    search_fields = (
        'title',
        'slug',
        'view_lists__name',
        'admin_lists__name',
        'owner__username',
        'owner__email',
        'edx_course_id',
    )
    inlines = [
        CollectionEdxEndpointInlineAdmin
    ]


class CollectionEdxEndpointAdmin(admin.ModelAdmin):
    """CollectionEdxEndpoint admin"""
    model = models.CollectionEdxEndpoint
    list_display = ('id', 'get_edx_endpoint_str', 'get_collection_title')

    def get_edx_endpoint_str(self, obj):  # pylint:disable=missing-docstring
        return "{} - {}".format(obj.edx_endpoint.name, obj.edx_endpoint.base_url)

    get_edx_endpoint_str.short_description = "EdX Endpoint"
    get_edx_endpoint_str.admin_order_field = "edx_endpoint__name"

    def get_collection_title(self, obj):  # pylint:disable=missing-docstring
        return obj.collection.title

    get_collection_title.short_description = "Collection"
    get_collection_title.admin_order_field = "collection__title"


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

    def has_add_permission(self, request, obj=None):
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
    autocomplete_fields = ['view_lists']
    list_display = (
        'title',
        'created_at',
    )
    list_filter = ['encode_jobs__state', 'status']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    search_fields = (
        'title',
        'description',
        'source_url',
        'collection__title',
        'view_lists__name',
    )


class VideoFileAdmin(admin.ModelAdmin):
    """Customized VideoFile admin model"""
    model = models.VideoFile
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    search_fields = ('video__title',)
    list_filter = ('encoding',)


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
    list_display = ('filename', 'language',)
    search_fields = ('filename', 'language', 'bucket_name', 'video__title',)


class VideoThumbnailAdmin(admin.ModelAdmin):
    """admin page of Moira list"""
    model = models.VideoThumbnail
    list_display = ('s3_object_key', 'video_id',)
    search_fields = ('bucket_name', 'video__title',)


admin.site.register(models.EdxEndpoint, EdxEndpointAdmin)
admin.site.register(models.Collection, CollectionAdmin)
admin.site.register(models.CollectionEdxEndpoint, CollectionEdxEndpointAdmin)
admin.site.register(models.MoiraList, MoiraListAdmin)
admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoFile, VideoFileAdmin)
admin.site.register(models.VideoThumbnail, VideoThumbnailAdmin)
admin.site.register(models.VideoSubtitle, VideoSubtitleAdmin)
admin.site.register(models.YouTubeVideo, YouTubeVideoAdmin)
