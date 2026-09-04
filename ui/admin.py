"""
Admin for UI app
"""

import re
from collections import Counter
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.contenttypes.admin import GenericTabularInline
from django.urls import reverse
from django.utils.html import format_html

from ui import api, models
from ui.constants import DescriptionFormat
from ui.html import (
    ALLOWED_DESCRIPTION_ATTRIBUTES,
    ALLOWED_DESCRIPTION_TAGS,
    attributes_in,
    sanitize_description,
    tags_in,
)
from ui.models import EncodeJob


class RichTextDescriptionAdminForm(forms.ModelForm):
    """
    Admin form for the rich-text `description` field.

    The OVS UI has a real editor; the admin has a plain textarea holding raw
    HTML, which is the easy place to break a description by hand. So rather than
    silently rewriting what an admin typed, this form:

      * says which tags are allowed, in help_text;
      * refuses the save and names what would have been removed, instead of
        quietly dropping it - an admin who pasted a heading should be told, not
        left wondering where it went;
      * refuses markup that does not round-trip (an unclosed tag), because the
        stored value is rendered as HTML on OVS and on MIT Learn.

    The API path sanitizes in the serializer instead of erroring, because there
    the editor has already constrained the input to the allowed vocabulary.
    """

    class Media:
        css = {"all": ("css/admin-rich-text.css",)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("description")
        if field is None:
            return
        field.help_text = format_html(
            "Checked as rich text only when <em>Description format</em> is "
            "\u201cRich text\u201d; a plain-text description is stored exactly as "
            "typed. Allowed tags: {tags}. Links keep only "
            "<code>href</code> and <code>title</code>; every other attribute is "
            "dropped. Headings are <strong>not</strong> supported - MIT Learn "
            "strips them. Prefer editing descriptions in the OVS collection or "
            "video dialog, which has a proper editor.",
            tags=", ".join(sorted(ALLOWED_DESCRIPTION_TAGS)),
        )
        field.widget.attrs.update(
            {
                "rows": 8,
                "class": "vLargeTextField rich-text-source",
                "spellcheck": "false",
            }
        )

    def clean(self):
        """
        Reject a rich-text description only when sanitizing would *lose* something.

        nh3 also normalizes harmlessly - it adds rel="noopener noreferrer" to
        every anchor and closes an unclosed tag - and refusing those would make
        the field unusable for correct input. So the rule is about loss, not
        about difference: a disallowed tag, a dropped attribute or a refused link
        scheme is the admin's intent silently disappearing, and that is worth an
        error. Tidying is accepted and stored in its tidied form.

        A plain-text description is left exactly as typed: it is rendered
        escaped, so there is nothing to strip, and running it through the
        allowlist would lose text rather than protect anything.

        Returns:
            dict: the cleaned data, with `description` in its tidied form

        Raises:
            forms.ValidationError: naming what would have been lost
        """
        cleaned_data = super().clean()
        if cleaned_data.get("description_format") != DescriptionFormat.HTML:
            return cleaned_data

        raw = cleaned_data.get("description") or ""
        cleaned = sanitize_description(raw)
        if not raw.strip() or cleaned == raw:
            return cleaned_data

        problems = []

        # Parsed, not pattern-matched: a regex over the source reads
        # "Q&A with the class = fun" as a class attribute and "Register online =
        # required" as an `on*` handler, refusing perfectly good prose.
        removed = sorted(tags_in(raw) - set(ALLOWED_DESCRIPTION_TAGS))
        if removed:
            tags = ", ".join(f"<{tag}>" for tag in removed)
            problems.append(
                f"these tags are not supported and would be removed: {tags}"
            )

        allowed_attributes = {
            attr for attrs in ALLOWED_DESCRIPTION_ATTRIBUTES.values() for attr in attrs
        }
        dropped = sorted(attributes_in(raw) - allowed_attributes)
        if dropped:
            attrs = ", ".join(dropped)
            problems.append(
                f"these attributes would be dropped: {attrs} "
                "(only href and title survive, and only on a link)"
            )

        refused_links = sorted(
            {
                (tag.get("href") or "").strip()
                for tag in BeautifulSoup(raw, "html5lib").find_all("a")
                if (tag.get("href") or "").strip()
                and not re.match(
                    r"(?:https?|mailto):", tag["href"].strip(), re.IGNORECASE
                )
            }
        )
        if refused_links:
            problems.append(
                "these links would lose their target - use an absolute http, "
                "https or mailto address: " + ", ".join(refused_links)
            )

        if problems:
            raise forms.ValidationError(
                {
                    "description": (
                        "This description was not saved, because publishing it "
                        "would change it: " + "; and ".join(problems) + "."
                    )
                }
            )

        # Nothing lost - nh3 only tidied the markup (closed a tag, added
        # rel="noopener noreferrer"). Store the tidied version.
        cleaned_data["description"] = cleaned
        return cleaned_data


class CollectionAdminForm(RichTextDescriptionAdminForm):
    """Collection admin form"""

    class Meta:
        model = models.Collection
        fields = "__all__"


class VideoAdminForm(RichTextDescriptionAdminForm):
    """Video admin form"""

    class Meta:
        model = models.Video
        fields = "__all__"


class ViewListsInline(admin.TabularInline):
    """Inline model for collection view_lists"""

    model = models.Collection.view_lists.through
    verbose_name = "View keycloak group"
    verbose_name_plural = "View keycloak groups"


class AdminListsInline(admin.TabularInline):
    """Inline model for collection admin_lists"""

    model = models.Collection.admin_lists.through
    verbose_name = "Admin keycloak groups"
    verbose_name_plural = "Admin keycloak groups"


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

    form = CollectionAdminForm

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
    list_filter = ["stream_source", "for_shorts", "include_in_learn"]
    list_display = ["title", "show_url", "include_in_learn", "for_shorts"]
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

    def save_model(self, request, obj, form, change):
        """Propagate is_public changes to all videos in the collection."""
        super().save_model(request, obj, form, change)
        if (
            change
            and "is_public" in form.changed_data
            and not (obj.is_public and obj.include_in_learn)
        ):
            obj.videos.update(is_public=obj.is_public, is_private=not obj.is_public)


class CollectionEdxEndpointAdmin(admin.ModelAdmin):
    """CollectionEdxEndpoint admin"""

    model = models.CollectionEdxEndpoint
    list_display = ("id", "get_edx_endpoint_str", "get_collection_title")

    def get_edx_endpoint_str(self, obj):
        return f"{obj.edx_endpoint.name} - {obj.edx_endpoint.base_url}"

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

    form = VideoAdminForm

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
    actions = ["retry_upload"]

    @admin.action(description="Retry upload for selected 'Upload failed' videos")
    def retry_upload(self, request, queryset):
        """Retry each selected 'Upload failed' video via api.retry_failed_upload and report outcomes."""
        tally = Counter(api.retry_failed_upload(video) for video in queryset)

        def report(count, message, level):
            if count:
                self.message_user(request, message.format(n=count), level=level)

        report(
            tally["retried"],
            "Re-queued upload for {n} video(s).",
            messages.SUCCESS,
        )
        report(
            tally["dispatch_failed"],
            "Failed to re-queue {n} video(s); status left as 'Upload failed'.",
            messages.ERROR,
        )
        report(
            tally["skipped_status"] + tally["skipped_conflict"],
            "Skipped {n} video(s) not in 'Upload failed' status.",
            messages.WARNING,
        )
        report(
            tally["skipped_no_source"],
            "Skipped {n} video(s) without a source_url.",
            messages.WARNING,
        )
        report(
            tally["skipped_no_original"],
            "Skipped {n} video(s) missing an original video file.",
            messages.WARNING,
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


class KeycloakGroupAdmin(admin.ModelAdmin):
    """admin page of Keycloak group"""

    model = models.KeycloakGroup
    list_display = ("name",)
    search_fields = ("name",)


class VideoSubtitleAdmin(admin.ModelAdmin):
    """admin page of Keycloak group"""

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
    """admin page of Keycloak group"""

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
admin.site.register(models.KeycloakGroup, KeycloakGroupAdmin)
admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoFile, VideoFileAdmin)
admin.site.register(models.VideoThumbnail, VideoThumbnailAdmin)
admin.site.register(models.VideoSubtitle, VideoSubtitleAdmin)
admin.site.register(models.YouTubeVideo, YouTubeVideoAdmin)
admin.site.register(EncodeJob, EncodeJobAdmin)
