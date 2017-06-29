"""
serializers for ui
"""
from django.utils.translation import ugettext_lazy
from rest_framework import serializers
from rest_framework.relations import RelatedField
from rest_framework.settings import api_settings

from ui.models import MoiraList, Video, VideoFile


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
        kwargs.pop('allow_empty', None)
        super(RelatedField, self).__init__(**kwargs)  # pylint: disable=bad-super-call

    def to_internal_value(self, data):
        kwargs = {self.attribute: data}
        instance, _ = self.model.objects.get_or_create(**kwargs)
        return instance

    def to_representation(self, value):
        return getattr(value, self.attribute)


class VideoSerializer(serializers.ModelSerializer):
    """Video Serializer"""
    moira_lists = SingleAttrRelatedField(model=MoiraList, attribute="name", many=True)

    class Meta:
        model = Video
        fields = ('id', 'created_at', 'title', 'description', 'moira_lists', 'videofile_set',)
        read_only_fields = ('id', 'created_at', 'videofile_set')


class VideoFileSerializer(serializers.ModelSerializer):
    """Video File Serializer"""
    class Meta:
        model = VideoFile
        fields = ('id', 'created_at', 's3_object_key', 'encoding', 'bucket_name')
        read_only_fields = ('id', 'created_at', 's3_object_key', 'encoding', 'bucket_name')


class DropboxFileSerializer(serializers.Serializer):
    """Dropbox File Serializer"""
    name = serializers.CharField()
    link = serializers.URLField()
    bytes = serializers.IntegerField(min_value=0)
    icon = serializers.URLField()
    thumbnailLink = serializers.URLField()
    isDir = serializers.BooleanField()
