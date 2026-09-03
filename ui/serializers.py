"""
serializers for ui
"""

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy
from rest_framework import serializers
from rest_framework.relations import RelatedField
from rest_framework.settings import api_settings

from ui import models
from ui import permissions as ui_permissions
from ui.constants import DescriptionFormat
from ui.encodings import EncodingNames
from ui.html import (
    description_as_html,
    sanitize_description,
    upgrade_description,
)
from ui.keycloak_utils import get_keycloak_client
from ui.utils import has_common_lists

User = get_user_model()


def validate_keycloak_groups(lists):
    """
    Raise a validation error if any of the groups in a list does not exist

    Args:
        lists(list of keycloak groups): List of groups

    Returns:
        (list of keycloak groups) List of groups
    """
    if not lists:
        return lists
    bad_lists = []
    keycloak_client = get_keycloak_client()
    for mlist in lists:
        group = keycloak_client.find_group_by_name(mlist.name)
        if not group:
            bad_lists.append(mlist.name)

    if bad_lists:
        raise serializers.ValidationError(
            f"Group does not exist: {','.join(bad_lists)}"
        )
    return lists


class RichTextDescriptionMixin:
    """
    Keeps a `description` safe for whatever its `description_format` says it is.

    A rich-text description is rendered as markup, on OVS's own pages and on MIT
    Learn, so it has to be sanitized on write whichever client sent it. See
    ui.html for the allowlist and why it is narrower than Learn's.

    A plain-text description is stored verbatim instead, and deliberately: it is
    only ever rendered escaped, so there is nothing to strip - and running it
    through the allowlist would *lose* text, since `a <b to c` would be read as
    an unterminated tag and dropped.
    """

    def validate(self, attrs):
        """
        Sanitize the description when the row is, or is becoming, rich text.

        Args:
            attrs (dict): the validated field values

        Returns:
            dict: attrs, with `description` sanitized where it needs to be
        """
        attrs = super().validate(attrs)

        # None on create: there is no stored description, so nothing to upgrade
        # from and nothing to preserve - whatever arrives is already in the
        # format the client declared.
        stored_format = getattr(self.instance, "description_format", None)
        effective_format = attrs.get(
            "description_format", stored_format or DescriptionFormat.TEXT
        )
        if effective_format != DescriptionFormat.HTML:
            return attrs

        if stored_format is not None and stored_format != DescriptionFormat.HTML:
            # Being upgraded. Whatever is in hand was written as plain text, so
            # convert it rather than sanitize it - escaping it is the whole
            # point, and passing it through the allowlist instead would read
            # `a <b to c` as an unterminated tag and drop the rest.
            #
            # This also closes the way round the allowlist: store anything while
            # the row is plain text (harmless, it renders escaped), then flip the
            # format on its own and have it rendered as markup unchecked.
            attrs["description"] = upgrade_description(
                attrs.get("description", self.instance.description)
            )
        elif "description" in attrs:
            attrs["description"] = sanitize_description(attrs["description"])

        return attrs

        if stored_format != DescriptionFormat.HTML:
            # Being upgraded. Whatever is in hand was written as plain text, so
            # convert it rather than sanitize it - escaping it is the whole
            # point, and passing it through the allowlist instead would read
            # `a <b to c` as an unterminated tag and drop the rest.
            #
            # This also closes the way round the allowlist: store anything while
            # the row is plain text (harmless, it renders escaped), then flip the
            # format on its own and have it rendered as markup unchecked.
            attrs["description"] = upgrade_description(
                attrs.get("description", self.instance.description)
            )
        elif "description" in attrs:
            attrs["description"] = sanitize_description(attrs["description"])

        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    class Meta:
        model = User
        fields = ("id", "username", "email")
        read_only_fields = ("id", "username", "email")


class SingleAttrRelatedField(RelatedField):
    """
    SingleAttrRelatedField serializer
    """

    def __init__(self, model, attribute="pk", **kwargs):
        self.model = model
        self.attribute = attribute
        # It would be nice to do this:
        #   super(SingleAttrRelatedField, self).__init__(**kwargs)
        # ...but unfortunately, that __init__() checks for a queryset,
        # and throws an exception if it's not there. Since this field doesn't
        # need a queryset, instead I'm reproducing the relevant code from that
        # __init__() method, and then calling its parent.
        self.html_cutoff = kwargs.pop(
            "html_cutoff", self.html_cutoff or int(api_settings.HTML_SELECT_CUTOFF)
        )
        self.html_cutoff_text = kwargs.pop(
            "html_cutoff_text",
            self.html_cutoff_text or gettext_lazy(api_settings.HTML_SELECT_CUTOFF_TEXT),
        )
        kwargs.pop("many", None)
        self.allow_empty = kwargs.pop("allow_empty", False)
        super(RelatedField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        kwargs = {self.attribute: data}
        instance, _ = self.model.objects.get_or_create(**kwargs)
        return instance

    def to_representation(self, value):
        return getattr(value, self.attribute)


class VideoFileSerializer(serializers.ModelSerializer):
    """Video File Serializer"""

    class Meta:
        model = models.VideoFile
        fields = (
            "id",
            "created_at",
            "s3_object_key",
            "encoding",
            "bucket_name",
            "cloudfront_url",
        )
        read_only_fields = (
            "id",
            "created_at",
            "s3_object_key",
            "encoding",
            "bucket_name",
            "cloudfront_url",
        )


class VideoThumbnailSerializer(serializers.ModelSerializer):
    """VideoThumbnail serializer"""

    class Meta:
        model = models.VideoThumbnail
        fields = ("id", "created_at", "s3_object_key", "bucket_name", "cloudfront_url")
        read_only_fields = (
            "id",
            "created_at",
            "s3_object_key",
            "bucket_name",
            "cloudfront_url",
        )


class VideoSubtitleSerializer(serializers.ModelSerializer):
    """VideoSubtitle serializer"""

    language_name = serializers.SerializerMethodField()

    def get_language_name(self, obj):
        """Get the language name"""
        return obj.language_name

    class Meta:
        model = models.VideoSubtitle
        fields = (
            "id",
            "created_at",
            "filename",
            "s3_object_key",
            "bucket_name",
            "language",
            "language_name",
        )
        read_only_fields = (
            "id",
            "created_at",
            "s3_object_key",
            "bucket_name",
            "language_name",
        )


class VideoSerializer(RichTextDescriptionMixin, serializers.ModelSerializer):
    """Video Serializer"""

    key = serializers.SerializerMethodField()
    collection_key = serializers.SerializerMethodField()
    collection_title = serializers.SerializerMethodField()
    cloudfront_url = serializers.SerializerMethodField()
    videofile_set = VideoFileSerializer(many=True, read_only=True)
    videothumbnail_set = VideoThumbnailSerializer(many=True, read_only=True)
    videosubtitle_set = VideoSubtitleSerializer(many=True)
    view_lists = SingleAttrRelatedField(
        model=models.KeycloakGroup, attribute="name", many=True, allow_empty=True
    )
    collection_view_lists = serializers.SerializerMethodField()

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    def get_collection_key(self, obj):
        """Get collection key"""
        return obj.collection.hexkey

    def get_collection_title(self, obj):
        """Get collection title"""
        return obj.collection.title

    def get_collection_view_lists(self, obj):
        """Get collection view lists"""
        return list(obj.collection.view_lists.values_list("name", flat=True))

    def validate_view_lists(self, value):
        """
        Validation for view-only keycloak groups

        Args:
            value(list of keycloak groups): list of keycloak groups

        Returns:
            (list of keycloak groups) List of keycloak groups
        """
        if value:
            return validate_keycloak_groups(value)
        return value

    def get_cloudfront_url(self, obj):
        """Get cloudfront_url"""
        if self.context.get("request") and ui_permissions.has_admin_permission(
            obj.collection, self.context["request"]
        ):
            video_file = obj.videofile_set.filter(encoding=EncodingNames.HLS).first()
            if obj.collection.allow_share_openedx and video_file:
                return video_file.cloudfront_url

        return ""

    class Meta:
        model = models.Video
        fields = (
            "key",
            "created_at",
            "title",
            "description",
            "description_format",
            "collection_key",
            "collection_title",
            "multiangle",
            "status",
            "videofile_set",
            "videothumbnail_set",
            "videosubtitle_set",
            "view_lists",
            "collection_view_lists",
            "is_public",
            "is_private",
            "is_logged_in_only",
            "sources",
            "youtube_id",
            "cloudfront_url",
            "cta_link",
        )
        read_only_fields = (
            "key",
            "created_at",
            "multiangle",
            "status",
            "videofile_set",
            "videothumbnail_set",
            "videosubtitle_set",
            "collection_view_lists",
            "sources",
            "youtube_id",
        )


class SimpleVideoSerializer(VideoSerializer):
    """
    Simplified video serializer for Collection view
    """

    class Meta:
        model = models.Video
        fields = (
            "key",
            "created_at",
            "title",
            "description",
            "description_format",
            "videofile_set",
            "videosubtitle_set",
            "is_public",
            "is_private",
            "view_lists",
            "collection_view_lists",
            "videothumbnail_set",
            "status",
            "collection_key",
            "cloudfront_url",
            "cta_link",
        )
        read_only_fields = fields


class CollectionSerializer(RichTextDescriptionMixin, serializers.ModelSerializer):
    """
    Serializer for Collection Model, used on collection detail page
    """

    key = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    view_lists = SingleAttrRelatedField(
        model=models.KeycloakGroup, attribute="name", many=True, allow_empty=True
    )
    admin_lists = SingleAttrRelatedField(
        model=models.KeycloakGroup, attribute="name", many=True, allow_empty=True
    )
    is_admin = serializers.SerializerMethodField()
    owner_info = UserSerializer(source="owner", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    def get_video_count(self, obj):
        """Custom getter for video count"""
        return obj.videos.count()

    def get_videos(self, obj):
        """Custom getter for videos"""
        if self.context.get("request"):
            user = self.context.get("request").user
            if user.is_anonymous:
                videos = obj.videos.filter(is_public=True)
            elif user.is_superuser or has_common_lists(
                user, list(obj.admin_lists.values_list("name", flat=True))
            ):
                videos = obj.videos.all()
            else:
                videos = obj.videos.filter(is_private=False)
        else:
            videos = obj.videos.all()
        return [
            SimpleVideoSerializer(video, context=self.context).data for video in videos
        ]

    def get_is_admin(self, obj):
        """Custom field to indicate whether or not the requesting user is an admin"""
        if self.context.get("request"):
            return ui_permissions.has_admin_permission(obj, self.context["request"])
        return False

    def validate_view_lists(self, value):
        """
        Validation for view-only keycloak groups
        Args:
            value(list of keycloak groups): list of keycloak groups

        Returns:
            (list of keycloak groups) List of keycloak groups
        """
        return validate_keycloak_groups(value)

    def validate_admin_lists(self, value):
        """
        Validation for admin keycloak groups

        Args:
            value(list of keycloak groups): list of keycloak groups

        Returns:
            (list of keycloak groups) List of keycloak groups
        """
        return validate_keycloak_groups(value)

    class Meta:
        model = models.Collection
        fields = (
            "key",
            "created_at",
            "title",
            "description",
            "description_format",
            "videos",
            "video_count",
            "view_lists",
            "admin_lists",
            "is_logged_in_only",
            "is_public",
            "stream_source",
            "edx_course_id",
            "is_admin",
            "owner",
            "owner_info",
        )
        read_only_fields = (
            "key",
            "created_at",
            "videos",
            "video_count",
            "is_admin",
            "is_public",
            "stream_source",
        )


class CollectionListSerializer(RichTextDescriptionMixin, serializers.ModelSerializer):
    """
    Serializer for Collection Model, used on collection lists page
    """

    key = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    view_lists = SingleAttrRelatedField(
        model=models.KeycloakGroup, attribute="name", many=True, allow_empty=True
    )
    admin_lists = SingleAttrRelatedField(
        model=models.KeycloakGroup, attribute="name", many=True, allow_empty=True
    )
    owner_info = UserSerializer(source="owner", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    def create(self, validated_data):
        if "owner" not in validated_data:
            validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    def get_video_count(self, obj):
        """Custom getter for video count"""
        return obj.videos.count()

    def validate_view_lists(self, value):
        """Validation for view-only keycloak groups"""
        return validate_keycloak_groups(value)

    def validate_admin_lists(self, value):
        """Validation for admin keycloak groups"""
        return validate_keycloak_groups(value)

    class Meta:
        model = models.Collection
        fields = (
            "key",
            "created_at",
            "title",
            "description",
            "description_format",
            "view_lists",
            "admin_lists",
            "video_count",
            "edx_course_id",
            "owner",
            "owner_info",
            "is_public",
            "stream_source",
        )
        read_only_fields = (
            "key",
            "created_at",
            "video_count",
            "is_public",
            "stream_source",
        )


class PublicCollectionSerializer(serializers.ModelSerializer):
    """Lightweight collection serializer for embedding in public video responses"""

    key = serializers.SerializerMethodField()
    # MIT Learn renders this with `dangerouslySetInnerHTML`, so it has to be
    # markup whatever the row stores. A plain-text description sent as-is would
    # lose its line breaks and be truncated at the first `<` followed by a
    # letter, which the browser reads as an unterminated tag.
    description = serializers.SerializerMethodField()

    def get_description(self, obj):
        """
        Return the description as HTML, whichever format it is stored in.

        Args:
            obj (Collection or Video): the object being serialized

        Returns:
            str: HTML
        """
        return description_as_html(obj.description, obj.description_format)

    def get_key(self, obj):
        """Return hex key"""
        return obj.hexkey

    class Meta:
        model = models.Collection
        fields = (
            "key",
            "title",
            "description",
            "is_public",
            "stream_source",
            "for_shorts",
        )


class PublicVideoSerializer(serializers.ModelSerializer):
    """Serializer for the public video list endpoint — includes embedded collection details"""

    key = serializers.SerializerMethodField()
    collection = PublicCollectionSerializer(read_only=True)
    videothumbnail_set = VideoThumbnailSerializer(many=True, read_only=True)
    videosubtitle_set = VideoSubtitleSerializer(many=True, read_only=True)
    sources = serializers.SerializerMethodField()
    # MIT Learn renders this with `dangerouslySetInnerHTML`, so it has to be
    # markup whatever the row stores. A plain-text description sent as-is would
    # lose its line breaks and be truncated at the first `<` followed by a
    # letter, which the browser reads as an unterminated tag.
    description = serializers.SerializerMethodField()

    def get_key(self, obj):
        """Return hex key"""
        return obj.hexkey

    def get_description(self, obj):
        """
        Return the description as HTML, whichever format it is stored in.

        Args:
            obj (Collection or Video): the object being serialized

        Returns:
            str: HTML
        """
        return description_as_html(obj.description, obj.description_format)

    def get_sources(self, obj):
        """Return only HLS sources"""
        return [
            {
                "src": f.cloudfront_url,
                "label": f.encoding,
                "type": "application/x-mpegURL",
            }
            for f in obj.hls_files
        ]

    class Meta:
        model = models.Video
        fields = (
            "key",
            "created_at",
            "title",
            "description",
            "status",
            "is_public",
            "youtube_id",
            "sources",
            "cta_link",
            "duration",
            "multiangle",
            "videothumbnail_set",
            "videosubtitle_set",
            "collection",
        )
        read_only_fields = fields


class DropboxFileSerializer(serializers.Serializer):
    """Dropbox File Serializer"""

    name = serializers.CharField()
    link = serializers.URLField()
    bytes = serializers.IntegerField(min_value=0)
    icon = serializers.URLField()
    thumbnailLink = serializers.URLField()
    isDir = serializers.BooleanField()


class DropboxUploadSerializer(serializers.Serializer):
    """Dropbox Upload Serializer"""

    collection = serializers.UUIDField()
    files = DropboxFileSerializer(many=True)


class ReplaceVideoSerializer(serializers.Serializer):
    """Serializer for replacing an existing video with a new Dropbox file"""

    video = serializers.UUIDField()
    file = DropboxFileSerializer()


class VideoSubtitleUploadSerializer(serializers.Serializer):
    """Caption File Serializer"""

    video = serializers.UUIDField()
    language = serializers.CharField()
    filename = serializers.CharField()

    def validate_filename(self, value):
        """Validate that the filename has a .srt or .vtt extension"""
        if not (value.endswith((".srt", ".vtt"))):
            raise serializers.ValidationError(
                "Only .srt and .vtt subtitle files are supported."
            )
        return value
