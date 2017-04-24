from datetime import datetime, timedelta
from rest_framework import serializers
from ui.models import Video


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ('created_at', 'title', 'description', 's3_object_key')
        read_only_fields = ('created_at', 's3_object_key')


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


class CloudFrontSignedURLSerializer(serializers.Serializer):
    key = serializers.CharField()
    expires_at = serializers.DateTimeField(required=False)
    duration = serializers.DurationField(required=False)

    def calculated_expiration(self, default_duration=timedelta(hours=2)):
        """
        Calculate the ``expires_at`` value. Uses the ``expires_at`` field
        if provided, otherwise uses the ``duration`` field if provided,
        otherwise uses a default duration.
        """
        self.is_valid()  # populate self.validated_data
        data = self.validated_data
        if "expires_at" in data:
            return data["expires_at"]
        elif "duration" in data:
            return datetime.utcnow() + data["duration"]
        else:
            return datetime.utcnow() + default_duration
