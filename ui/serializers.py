"""
serializers for ui
"""
from django.utils.translation import ugettext_lazy
from rest_framework import serializers
from rest_framework.relations import RelatedField
from rest_framework.settings import api_settings

from ui import models, permissions as ui_permissions
from ui.encodings import EncodingNames
from ui.utils import get_moira_client


def validate_moira_lists(lists):
    """
    Raise a validation error if any of the moira lists in a list does not exist or is not a mailing list

    Args:
        lists(list of MoiraList): List of moira lists

    Returns:
        (list of MoiraList) List of moira lists
    """
    bad_lists = []
    moira_client = get_moira_client()
    for mlist in lists:
        if not moira_client.list_exists(mlist.name):
            bad_lists.append(mlist.name)
    if bad_lists:
        raise serializers.ValidationError("Moira list does not exist: {}".format(','.join(bad_lists)))
    return lists


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
            'html_cutoff',
            self.html_cutoff or int(api_settings.HTML_SELECT_CUTOFF)
        )
        self.html_cutoff_text = kwargs.pop(
            'html_cutoff_text',
            self.html_cutoff_text or ugettext_lazy(api_settings.HTML_SELECT_CUTOFF_TEXT)
        )
        kwargs.pop('many', None)
        self.allow_empty = kwargs.pop('allow_empty', False)
        super(RelatedField, self).__init__(**kwargs)  # pylint: disable=bad-super-call

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
        fields = ('id', 'created_at', 's3_object_key', 'encoding', 'bucket_name', 'cloudfront_url')
        read_only_fields = ('id', 'created_at', 's3_object_key', 'encoding', 'bucket_name', 'cloudfront_url')


class VideoThumbnailSerializer(serializers.ModelSerializer):
    """VideoThumbnail serializer"""
    class Meta:
        model = models.VideoThumbnail
        fields = ('id', 'created_at', 's3_object_key', 'bucket_name')
        read_only_fields = ('id', 'created_at', 's3_object_key', 'bucket_name')


class VideoSubtitleSerializer(serializers.ModelSerializer):
    """VideoSubtitle serializer"""
    language_name = serializers.SerializerMethodField()

    def get_language_name(self, obj):
        """Get the language name"""
        return obj.language_name

    class Meta:
        model = models.VideoSubtitle
        fields = ('id', 'created_at', 'filename', 's3_object_key', 'bucket_name', 'language', 'language_name')
        read_only_fields = ('id', 'created_at', 's3_object_key', 'bucket_name', 'language_name')


class VideoSerializer(serializers.ModelSerializer):
    """Video Serializer"""
    key = serializers.SerializerMethodField()
    collection_key = serializers.SerializerMethodField()
    collection_title = serializers.SerializerMethodField()
    cloudfront_url = serializers.SerializerMethodField()
    videofile_set = VideoFileSerializer(many=True, read_only=True)
    videothumbnail_set = VideoThumbnailSerializer(many=True, read_only=True)
    videosubtitle_set = VideoSubtitleSerializer(many=True)
    view_lists = SingleAttrRelatedField(
        model=models.MoiraList, attribute="name", many=True, allow_empty=True
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
        return list(obj.collection.view_lists.values_list('name', flat=True))

    def validate_view_lists(self, value):
        """
        Validation for view-only moira lists

        Args:
            value(list of MoiraList): list of moira lists

        Returns:
            (list of MoiraList) List of moira lists
        """
        return validate_moira_lists(value)

    def get_cloudfront_url(self, obj):
        """Get cloudfront_url"""
        if self.context.get('request') and ui_permissions.has_admin_permission(obj.collection, self.context['request']):
            video_file = obj.videofile_set.filter(encoding=EncodingNames.HLS).first()
            if obj.collection.allow_share_openedx and video_file:
                return video_file.cloudfront_url

        return ""

    class Meta:
        model = models.Video
        fields = (
            'key',
            'created_at',
            'title',
            'description',
            'collection_key',
            'collection_title',
            'multiangle',
            'status',
            'videofile_set',
            'videothumbnail_set',
            'videosubtitle_set',
            'view_lists',
            'collection_view_lists',
            'is_public',
            'is_private',
            'sources',
            'youtube_id',
            'cloudfront_url'
        )
        read_only_fields = (
            'key',
            'created_at',
            'multiangle',
            'status',
            'videofile_set',
            'videothumbnail_set',
            'videosubtitle_set',
            'collection_view_lists',
            'sources',
            'youtube_id'
        )


class SimpleVideoSerializer(VideoSerializer):
    """
    Simplified video serializer for Collection view
    """
    class Meta:
        model = models.Video
        fields = (
            'key',
            'created_at',
            'title',
            'description',
            'videofile_set',
            'videosubtitle_set',
            'is_public',
            'is_private',
            'view_lists',
            'collection_view_lists',
            'videothumbnail_set',
            'status',
            'collection_key',
            'cloudfront_url'
        )
        read_only_fields = fields


class CollectionSerializer(serializers.ModelSerializer):
    """
    Serializer for Collection Model, used on collection detail page
    """
    key = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    view_lists = SingleAttrRelatedField(
        model=models.MoiraList, attribute="name", many=True, allow_empty=True
    )
    admin_lists = SingleAttrRelatedField(
        model=models.MoiraList, attribute="name", many=True, allow_empty=True
    )
    is_admin = serializers.SerializerMethodField()

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    def get_video_count(self, obj):
        """Custom getter for video count"""
        return obj.videos.count()

    def get_videos(self, obj):
        """Custom getter for videos"""
        if self.context.get('request') and self.context.get('request').user.is_anonymous:
            videos = obj.videos.filter(is_public=True)
        else:
            videos = obj.videos.all()
        return [SimpleVideoSerializer(video, context=self.context).data for video in videos]

    def get_is_admin(self, obj):
        """Custom field to indicate whether or not the requesting user is an admin"""
        if self.context.get('request'):
            return ui_permissions.has_admin_permission(obj, self.context['request'])
        return None

    def validate_view_lists(self, value):
        """
        Validation for view-only moira lists

        Args:
            value(list of MoiraList): list of moira lists

        Returns:
            (list of MoiraList) List of moira lists
        """
        return validate_moira_lists(value)

    def validate_admin_lists(self, value):
        """
        Validation for admin moira lists

        Args:
            value(list of MoiraList): list of moira lists

        Returns:
            (list of MoiraList) List of moira lists
        """
        return validate_moira_lists(value)

    class Meta:
        model = models.Collection
        fields = (
            'key',
            'created_at',
            'title',
            'description',
            'videos',
            'video_count',
            'view_lists',
            'admin_lists',
            'is_admin',
        )
        read_only_fields = (
            'key',
            'created_at',
            'videos',
            'video_count',
            'is_admin',
        )


class CollectionListSerializer(serializers.ModelSerializer):
    """
    Serializer for Collection Model, used on collection lists page
    """
    key = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    view_lists = SingleAttrRelatedField(
        model=models.MoiraList, attribute="name", many=True, allow_empty=True
    )
    admin_lists = SingleAttrRelatedField(
        model=models.MoiraList, attribute="name", many=True, allow_empty=True
    )

    def create(self, validated_data):
        return super().create({
            **validated_data,
            "owner": self.context["request"].user
        })

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    def get_video_count(self, obj):
        """Custom getter for video count"""
        return obj.videos.count()

    def validate_view_lists(self, value):
        """Validation for view-only moira lists"""
        return validate_moira_lists(value)

    def validate_admin_lists(self, value):
        """Validation for admin moira lists"""
        return validate_moira_lists(value)

    class Meta:
        model = models.Collection
        fields = (
            'key',
            'created_at',
            'title',
            'description',
            'view_lists',
            'admin_lists',
            'video_count',
        )
        read_only_fields = (
            'key',
            'created_at',
            'video_count',
        )


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


class VideoSubtitleUploadSerializer(serializers.Serializer):
    """Caption File Serializer"""
    video = serializers.UUIDField()
    language = serializers.CharField()
    filename = serializers.CharField()
