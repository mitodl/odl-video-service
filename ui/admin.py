"""
Admin for UI app
"""

from urllib.parse import urljoin

from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.urls import reverse
from django.utils.html import format_html

from ui import models
from ui.models import EncodeJob


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
    list_display = ("id", "name", "base_url")
    exclude = ("is_global_default",)


class CollectionEdxEndpointInlineAdmin(admin.StackedInline):
    """CollectionEdxEndpoint inline admin"""

    model = models.CollectionEdxEndpoint
    extra = 1
    # we're not going to associate a collection with more than 1 endpoint anything in the near future
    max_num = 1


class CollectionAdmin(admin.ModelAdmin):
    """Customized collection admin model"""

    def show_url(self, obj):
        """Display the collection URL"""
        url = urljoin(
            settings.ODL_VIDEO_BASE_URL,
            reverse("collection-react-view", kwargs={"collection_key": obj.hexkey}),
        )
        return format_html("<a href='{url}'>{url}</a>", url=url)

    def get_fields(self, request, obj=None):
        """Add show_url to the beginning of model fields"""
        return ["show_url"] + super().get_fields(request, obj)

    show_url.short_description = "URL"
    show_url.mark_safe = True

    date_hierarchy = "created_at"
    readonly_fields = ["show_url", "created_at"]
    list_filter = ["stream_source"]
    list_display = ["title", "show_url"]
    autocomplete_fields = ["owner", "view_lists", "admin_lists"]
    search_fields = (
        "title",
        "slug",
        "view_lists__name",
        "admin_lists__name",
        "owner__username",
        "owner__email",
        "edx_course_id",
    )
    inlines = [CollectionEdxEndpointInlineAdmin]


class CollectionEdxEndpointAdmin(admin.ModelAdmin):
    """CollectionEdxEndpoint admin"""

    model = models.CollectionEdxEndpoint
    list_display = ("id", "get_edx_endpoint_str", "get_collection_title")

    def get_edx_endpoint_str(self, obj):
        return "{} - {}".format(obj.edx_endpoint.name, obj.edx_endpoint.base_url)

    get_edx_endpoint_str.short_description = "EdX Endpoint"
    get_edx_endpoint_str.admin_order_field = "edx_endpoint__name"

    def get_collection_title(self, obj):
        return obj.collection.title

    get_collection_title.short_description = "Collection"
    get_collection_title.admin_order_field = "collection__title"


class VideoFilesInline(admin.TabularInline):
    """Inline model for video files"""

    model = models.VideoFile
    extra = 0
    readonly_fields = ["created_at"]


class VideoSubtitlesInline(admin.TabularInline):
    """Inline model for video videoSubtitles"""

    model = models.VideoSubtitle
    extra = 0
    readonly_fields = ["created_at"]


class VideoThumbnailsInline(admin.TabularInline):
    """Inline model for video thumbnails"""

    model = models.VideoThumbnail
    extra = 0
    readonly_fields = ["created_at"]


class VideoEncodeJobsInline(GenericTabularInline):
    """
    Inline model for video encode job
    """

    model = EncodeJob
    extra = 0
    list_display = ("id", "state", "message")
    readonly_fields = ("id", "state", "message")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method != "POST"

    def has_delete_permission(self, request, obj=None):
        return False


class VideoAdmin(admin.ModelAdmin):
    """Customized Video admin model"""

    def show_url(self, obj):
        """Display the video URL"""
        url = urljoin(
            settings.ODL_VIDEO_BASE_URL,
            reverse("video-detail", kwargs={"video_key": obj.hexkey}),
        )
        return format_html("<a href='{url}'>{url}</a>", url=url)

    def get_fields(self, request, obj=None):
        """Add show_url to the beginning of model fields"""
        return ["show_url"] + super().get_fields(request, obj)

    show_url.short_description = "URL"
    show_url.mark_safe = True

    model = models.Video
    inlines = [
        VideoEncodeJobsInline,
        VideoFilesInline,
        VideoSubtitlesInline,
        VideoThumbnailsInline,
    ]
    autocomplete_fields = ["view_lists", "collection"]
    list_display = (
        "title",
        "created_at",
        "show_url",
    )
    list_filter = ["encode_jobs__state", "status"]
    date_hierarchy = "created_at"
    readonly_fields = ["show_url", "created_at"]
    search_fields = (
        "title",
        "description",
        "source_url",
        "collection__title",
        "view_lists__name",
    )


class VideoFileAdmin(admin.ModelAdmin):
    """Customized VideoFile admin model"""

    model = models.VideoFile
    date_hierarchy = "created_at"
    readonly_fields = ["created_at"]
    search_fields = ("video__title",)
    list_filter = ("encoding",)


class YouTubeVideoAdmin(admin.ModelAdmin):
    """Customized YouTubeVideo admin model"""

    model = models.YouTubeVideo
    list_display = (
        "id",
        "created_at",
        "status",
        "video_title",
        "video_key",
        "video_collection",
    )
    list_filter = ["status", "video__collection"]
    search_fields = ["id", "video__key", "video__title"]

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
    list_display = ("name",)
    search_fields = ("name",)


class VideoSubtitleAdmin(admin.ModelAdmin):
    """admin page of Moira list"""

    model = models.VideoSubtitle
    list_display = (
        "filename",
        "language",
    )
    search_fields = (
        "filename",
        "language",
        "bucket_name",
        "video__title",
    )


class VideoThumbnailAdmin(admin.ModelAdmin):
    """admin page of Moira list"""

    model = models.VideoThumbnail
    list_display = (
        "s3_object_key",
        "video_id",
    )
    search_fields = (
        "bucket_name",
        "video__title",
    )


class EncodeJobAdmin(admin.ModelAdmin):
    """EncodeJob admin"""

    model = EncodeJob
    list_display = ("id", "state", "message")
    list_filters = ("state",)
    search_fields = ("id", "message")
    readonly_fields = ("created_at",)


admin.site.register(models.EdxEndpoint, EdxEndpointAdmin)
admin.site.register(models.Collection, CollectionAdmin)
admin.site.register(models.CollectionEdxEndpoint, CollectionEdxEndpointAdmin)
admin.site.register(models.MoiraList, MoiraListAdmin)
admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoFile, VideoFileAdmin)
admin.site.register(models.VideoThumbnail, VideoThumbnailAdmin)
admin.site.register(models.VideoSubtitle, VideoSubtitleAdmin)
admin.site.register(models.YouTubeVideo, YouTubeVideoAdmin)
admin.site.register(EncodeJob, EncodeJobAdmin)
