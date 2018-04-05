"""
Models for UI app
"""
import os
from uuid import uuid4

import boto3
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.conf import settings
from dj_elastictranscoder.models import EncodeJob
from pycountry import languages


from mail import tasks
from ui import utils
from ui.constants import VideoStatus, YouTubeStatus, StreamSource
from ui.encodings import EncodingNames
from ui.tasks import delete_s3_objects

TRANSCODE_PREFIX = 'transcoded'


class MoiraList(models.Model):
    """
    Model for Moira
    """
    name = models.CharField(max_length=250, unique=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<MoiraList: {self.name!r}>'.format(self=self)


class CollectionManager(models.Manager):
    """
    Custom manager for the Collection model
    """

    def all_viewable(self, user):
        """
        Return all collections that a user has view permissions for.  Currently not used. Only
        users who are admins can see a list of collections (via `get_collections_editable`).

        Args:
            user (django.contrib.auth.User): the Django user.

        Returns:
            A list of collections the user has view access to.
        """
        if user.is_superuser:
            return self.all()
        moira_list_qset = MoiraList.objects.filter(name__in=utils.user_moira_lists(user))
        return self.filter(
            models.Q(view_lists__in=moira_list_qset) |
            models.Q(admin_lists__in=moira_list_qset) |
            models.Q(owner=user)).distinct()

    def all_admin(self, user):
        """
        Return all collections that a user has admin permissions for.

        Args:
            user (django.contrib.auth.User): the Django user.

        Returns:
            A list of collections the user has admin access to.

        """
        if user.is_superuser:
            return self.all()
        return self.filter(
            models.Q(admin_lists__in=MoiraList.objects.filter(name__in=utils.user_moira_lists(user))) |
            models.Q(owner=user)).distinct()


class Collection(models.Model):
    """
    Model for Video Collections
    """
    key = models.UUIDField(unique=True, null=False, blank=False, default=uuid4)
    title = models.TextField()
    description = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    view_lists = models.ManyToManyField(MoiraList, blank=True, related_name='view_lists')
    admin_lists = models.ManyToManyField(MoiraList, blank=True, related_name='admin_lists')
    created_at = models.DateTimeField(auto_now_add=True)
    stream_source = models.CharField(
        null=True,
        blank=True,
        choices=[(status, status) for status in StreamSource.ALL_SOURCES],
        max_length=10
    )

    objects = CollectionManager()

    class Meta:
        ordering = ['-created_at', ]

    def __str__(self):
        return self.title

    def __repr__(self):
        return '<Collection: title="{self.title!r}", owner={self.owner.username!r}>'.format(self=self)

    @property
    def hexkey(self):
        """
        Return the hex representation of the key
        """
        return self.key.hex

    @classmethod
    def for_owner(cls, owner):
        """
        Returns a queryset of all the objects filtered by owner
        """
        return cls.objects.filter(owner=owner)


class Video(models.Model):
    """
    Represents an uploaded video, primarily in terms of metadata (source url, title, etc).
    The actual video files (original and encoded) are represented by the VideoFile model.
    """
    key = models.UUIDField(unique=True, null=False, blank=False, default=uuid4)
    collection = models.ForeignKey(Collection, related_name='videos')
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=250, blank=False)
    description = models.TextField(blank=True)
    source_url = models.URLField()
    status = models.CharField(
        null=False,
        default=VideoStatus.CREATED,
        choices=[(status, status) for status in VideoStatus.ALL_STATUSES],
        max_length=50,
    )
    encode_jobs = GenericRelation(EncodeJob)
    multiangle = models.BooleanField(null=False, default=False)
    view_lists = models.ManyToManyField(MoiraList, blank=True, related_name='video_view_lists')
    is_public = models.BooleanField(null=False, default=False)
    is_private = models.BooleanField(null=False, default=False)

    class Meta:
        ordering = ['-created_at', ]

    @property
    def hexkey(self):
        """
        Return the hex representation of the key
        """
        return self.key.hex

    @property
    def admin_lists(self):
        """
        Return the video collection's admin lists
        """
        return self.collection.admin_lists

    @property
    def youtube_id(self):
        """
        Return YouTube video id if any
        """
        try:
            youtube_video = self.youtubevideo
            if youtube_video.status == YouTubeStatus.PROCESSED:
                return youtube_video.id
            return None
        except YouTubeVideo.DoesNotExist:
            return None

    @property
    def original_video(self):
        """
        Return the original VideoFile if it exists
        """
        return self.videofile_set.filter(encoding=EncodingNames.ORIGINAL).first()

    @property
    def transcoded_videos(self):
        """
        Return the transcoded videofiles, in order from highest resolution to lowest, if applicable (ie MP4)

        Returns:
            list: sorted list of transcoded VideoFile objects, from highest to lowest resolution
        """
        return sorted(self.videofile_set.exclude(encoding=EncodingNames.ORIGINAL),
                      key=lambda x: EncodingNames.MP4.index(x.encoding) if x.encoding in EncodingNames.MP4 else 0)

    @property
    def sources(self):
        """
        Generate a sources dict for VideoJS

        Returns:
            dict: Dict of video sources for VideoJS
        """
        if self.is_public and self.collection.stream_source == StreamSource.YOUTUBE and self.youtube_id is not None:
            return []
        sources = [
            {
                "src": file.cloudfront_url,
                "label": file.encoding,
                "type":  "application/x-mpegURL" if file.encoding == EncodingNames.HLS else "video/mp4"
            } for file in self.transcoded_videos
        ]
        return sources

    def get_s3_key(self):
        """
        Avoid duplicate S3 keys/filenames when transferring videos from Dropbox

        Args:
            user_id (str): The user who is uploading a new video
            key (str): The base key to check for duplicates

        Returns:
            str: A unique S3 key including the user id as a virtual subfolder
        """
        _, extension = os.path.splitext(self.source_url.split('/')[-1])
        newkey = '{uuid}/video{ext}'.format(uuid=str(self.hexkey), ext=extension)
        return newkey

    def transcode_key(self, preset=None):
        """
        Get the S3 key for a video playlist file

        Args:
            encoding(str): The encoding preset to use (should be one included in settings.ET_PRESET_IDS)

        Returns:
            str: The S3 key to used for the encoded file.
        """
        original_s3_key = self.videofile_set.get(encoding='original').s3_object_key
        if not preset:
            return original_s3_key
        output_template = '{prefix}/{s3key}_{preset}'
        basename, _ = os.path.splitext(original_s3_key)
        return output_template.format(prefix=TRANSCODE_PREFIX, s3key=basename, preset=preset)

    def subtitle_key(self, dttm, language='en', prefix='subtitles'):
        """
        Returns an S3 object key to be used for a subtitle file
        Args:
            language(str): 2-letter language code
            dttm(DateTime): a DateTime object
            prefix(str): beginning of S3 key

        Returns:
            str: S3 object key
        """
        return '{prefix}/{key}/subtitles_{key}_{dt}_{lang}.vtt'.format(
            prefix=prefix,
            key=self.hexkey,
            dt=dttm.strftime('%Y%m%d%H%M%S'),
            lang=language
        )

    def update_status(self, status):
        """
        Assign and save the status of a Video

        Args:
            status(str): The status to assign the video
        """
        self.status = status
        self.save()
        if status in tasks.STATUS_TO_NOTIFICATION.keys():
            tasks.async_send_notification_email.delay(self.id)

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        """
        Overridden method to run a preventive validation before saving the object.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or "<untitled video>"

    def __repr__(self):
        return '<Video: {self.title!r} {self.key!r}>'.format(self=self)


class VideoS3(models.Model):
    """
    Abstract class with methods/properties common to both VideoFile and VideoThumbnail models
    """

    created_at = models.DateTimeField(auto_now_add=True)
    s3_object_key = models.TextField(unique=True, blank=False, null=False)
    bucket_name = models.CharField(max_length=63, blank=False, null=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    preset_id = models.CharField(max_length=128, blank=True, null=True)

    @property
    def s3_object(self):
        """
        Get the S3 Object for the video

            Returns:
                s3.Object: Video file's S3 object
        """
        s3 = boto3.resource('s3')
        return s3.Object(self.bucket_name, self.s3_object_key)

    @property
    def s3_url(self):
        """
        URL for the Video S3 object

        Returns:
            str: URL
        """
        return "https://{domain}/{bucket}/{key}".format(
            domain=settings.AWS_S3_DOMAIN,
            bucket=self.bucket_name,
            key=self.s3_object_key,
        )

    @property
    def s3_basename(self):
        """
        The S3 object key without any file extensions

        Returns:
            str: S3 base key name
        """
        return os.path.splitext(self.s3_object_key)[0]

    @property
    def cloudfront_url(self):
        """
        Get the Cloudfront URL for the video

        Returns:
            str: Cloudfront unsigned URL
        """
        distribution = settings.VIDEO_CLOUDFRONT_DIST
        if not distribution:
            raise RuntimeError("Missing required setting: VIDEO_CLOUDFRONT_DIST")
        return "https://{dist}.cloudfront.net/{key}".format(
            dist=distribution,
            key=self.s3_object_key
        )

    def delete_from_s3(self):
        """
        Delete the S3 object for this this thumbnail
        """
        delete_s3_objects.delay(self.bucket_name, self.s3_object_key)

    class Meta:
        abstract = True


class VideoFile(VideoS3):
    """
    A file associated with a Video object, either the original upload or a transcoded file.
    """
    encoding = models.CharField(max_length=128, default=EncodingNames.ORIGINAL)

    def delete_from_s3(self):
        """
        HLS encoding creates multiple S3 objects, use this method to delete them all.
        """
        if self.encoding == EncodingNames.HLS:
            key = os.path.dirname(self.s3_object_key)
            delete_s3_objects.delay(self.bucket_name, key, as_filter=True)
        else:
            super().delete_from_s3()

    def __str__(self):
        return '{}: {} encoding'.format(self.video.title, self.encoding)

    def __repr__(self):
        return '<VideoFile: {self.video.title!r} {self.s3_object_key!r} {self.encoding!r}>'.format(self=self)


class VideoThumbnail(VideoS3):
    """
    A thumbnail associated with a video object; the number of thumbnails for a video
    will depend on the length of the video.
    """
    max_width = models.IntegerField(null=True, blank=True)
    max_height = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '{}: {}'.format(self.video.title, self.s3_object_key)

    def __repr__(self):
        return '<VideoThumbnail: {self.s3_object_key!r} {self.max_width!r} {self.max_height!r}>'.format(self=self)


class VideoSubtitle(VideoS3):
    """A VTT file that provides captions for a Video"""
    filename = models.CharField(max_length=1024, null=False, blank=True)
    language = models.CharField(max_length=2, null=False, blank=True, default=languages.get(name='English').alpha_2)
    unique_together = (("video", "language"),)

    @property
    def language_name(self):
        """
        Gets the name associated with the language code
        """
        return languages.get(alpha_2=self.language).name

    def __str__(self):
        return '{}: {}: {}'.format(self.video.title, self.s3_object_key, self.language)

    def __repr__(self):
        return '<VideoSubtitle: {self.s3_object_key!r} {self.language!r} >'.format(self=self)


class YouTubeVideo(models.Model):
    """A YouTube version of the video"""
    video = models.OneToOneField(Video, on_delete=models.CASCADE, primary_key=True)
    id = models.CharField(max_length=11, null=True)
    status = models.CharField(null=False, default=YouTubeStatus.UPLOADING, max_length=24)

    def __repr__(self):
        return '<YouTubeVideo: {self.id!r} {self.video.title!r} {self.video.hexkey!r} >'.format(self=self)

    def __str__(self):
        return '{}: {}: {}'.format(self.id, self.video.title, self.video.hexkey)
