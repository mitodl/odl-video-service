from datetime import datetime, timedelta
from rest_framework import serializers
from ui.models import Video


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ('id', 'created_at', 'title', 'description', 's3_object_key')
        read_only_fields = ('id', 'created_at', 's3_object_key')


class DropboxFileSerializer(serializers.Serializer):
    name = serializers.CharField()
    link = serializers.URLField()
    bytes = serializers.IntegerField(min_value=0)
    icon = serializers.URLField()
    thumbnailLink = serializers.URLField()
    isDir = serializers.BooleanField()

    def create(self, validated_data):
        video, created = Video.objects.get_or_create(
            s3_object_key=validated_data["name"],
            defaults={'source_url': validated_data["link"]},
        )
        return video
