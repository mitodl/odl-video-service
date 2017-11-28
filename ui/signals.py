"""
ui model signals
"""
from django.conf import settings
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

from cloudsync.tasks import upload_youtube_video, remove_youtube_video, remove_youtube_caption
from ui.models import VideoFile, VideoThumbnail, VideoSubtitle, Video, YouTubeVideo

# pylint: disable=unused-argument


@receiver(pre_delete, sender=VideoFile)
@receiver(pre_delete, sender=VideoThumbnail)
@receiver(pre_delete, sender=VideoSubtitle)
def delete_s3_files(sender, **kwargs):
    """
    Make sure S3 files are deleted along with associated video file/thumbnail object
    """
    kwargs['instance'].delete_from_s3()


@receiver(pre_delete, sender=VideoSubtitle)
def update_video_permissions(sender, **kwargs):
    """
    Remove public video permissions if the subtitle is about to be deleted and no other subtitles exist.
    Otherwise just delete the subtitle from Youtube.
    """
    if settings.ENABLE_VIDEO_PERMISSIONS:
        video = kwargs['instance'].video
        if video.is_public:
            if len(video.videosubtitle_set.all()) <= 1:
                video.is_public = False
                video.save()
            elif video.youtube_id:
                remove_youtube_caption.delay(video.id, kwargs['instance'].language)


@receiver(pre_delete, sender=YouTubeVideo)
def delete_youtube_video(sender, **kwargs):
    """
    Call the YouTube API to delete a video
    """
    if settings.ENABLE_VIDEO_PERMISSIONS:
        remove_youtube_video.delay(kwargs['instance'].id)


@receiver(post_save, sender=Video)
def sync_youtube(sender, **kwargs):
    """

    Upload a video to youtube if it is public and not already on YouTube.
    Delete from youtube if it is there and permissions are not public.
    """
    if settings.ENABLE_VIDEO_PERMISSIONS:
        video = kwargs['instance']
        yt_video_id = video.youtube_id
        if video.is_public:
            if not yt_video_id:
                upload_youtube_video.delay(video.id)
        elif yt_video_id:
            YouTubeVideo.objects.get(id=yt_video_id).delete()
