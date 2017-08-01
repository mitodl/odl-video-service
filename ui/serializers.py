"""
serializers for ui
"""
from django.utils.translation import ugettext_lazy
from rest_framework import serializers
from rest_framework.relations import RelatedField
from rest_framework.settings import api_settings

from ui import models


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
        fields = ('id', 'created_at', 's3_object_key', 'encoding', 'bucket_name')
        read_only_fields = ('id', 'created_at', 's3_object_key', 'encoding', 'bucket_name')


class VideoThumbnailSerializer(serializers.ModelSerializer):
    """VideoThumbnail serializer"""
    class Meta:
        model = models.VideoThumbnail
        fields = ('id', 'created_at', 's3_object_key', 'bucket_name')
        read_only_fields = ('id', 'created_at', 's3_object_key', 'bucket_name')


class VideoSerializer(serializers.ModelSerializer):
    """Video Serializer"""
    key = serializers.SerializerMethodField()
    videofile_set = VideoFileSerializer(many=True, read_only=True)
    videothumbnail_set = VideoThumbnailSerializer(many=True, read_only=True)

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    class Meta:
        model = models.Video
        fields = (
            'key',
            'created_at',
            'title',
            'description',
            'videofile_set',
            'videothumbnail_set',
        )
        read_only_fields = (
            'key',
            'created_at',
        )


class CollectionSerializer(serializers.ModelSerializer):
    """
    Serializer for Collection Model
    """
    key = serializers.SerializerMethodField()
    videos = VideoSerializer(many=True, read_only=True)

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    class Meta:
        model = models.Collection
        fields = (
            'key',
            'title',
            'description',
            'owner',
            'videos',
            'moira_lists',
        )
        read_only_fields = (
            'key',
        )


class CollectionListSerializer(serializers.ModelSerializer):
    """
    Serializer for Collection Model
    """
    key = serializers.SerializerMethodField()

    def get_key(self, obj):
        """Custom getter for the key"""
        return obj.hexkey

    class Meta:
        model = models.Collection
        fields = (
            'key',
            'title',
            'description',
            'owner',
        )
        read_only_fields = (
            'key',
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
