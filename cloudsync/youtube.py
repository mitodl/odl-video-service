""" YouTube API interface"""
import http
import time
import logging
from tempfile import NamedTemporaryFile

import boto3
import httplib2
import oauth2client

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

log = logging.getLogger(__name__)

# Quota errors may contain either one of the following
API_QUOTA_ERROR_MSG = 'dailyLimitExceeded'


class YouTubeUploadException(Exception):
    """Custom exception for YouTube uploads"""


def resumable_upload(request, max_retries=10):
    """
    Upload a video to YouTube and resume on failure up to 10 times, adapted from YouTube API example.
    To use resumable media you must use a MediaFileUpload object and flag it as a resumable upload.
    You then repeatedly call next_chunk() on the googleapiclient.http.HttpRequest object until the
    upload is complete.

    Args:
        request(googleapiclient.http.HttpRequest): The Youtube API execute request to process
        max_retries(int): Maximum # of times to retry an upload (default 10)

    Returns:
        dict: The YouTube API response
    """
    response = None
    error = None

    retry = 0
    retry_exceptions = (OSError, http.client.HTTPException)
    retry_statuses = [500, 502, 503, 504]

    while response is None:
        try:
            _, response = request.next_chunk()
            if response is not None and 'id' not in response:
                raise YouTubeUploadException('YouTube upload failed: %s', response)
        except HttpError as e:
            if e.resp.status in retry_statuses:
                error = e
            else:
                raise
        except retry_exceptions as e:
            error = e

        if error is not None:
            retry += 1
            if retry > max_retries:
                log.error('Final upload failure', exc_info=error)
                raise YouTubeUploadException('Retried YouTube upload 10x, giving up') from error
            sleep_time = 2 ** retry
            time.sleep(sleep_time)

    return response


class YouTubeApi:
    """
    Class interface to YouTube API calls
    """

    client = None
    s3 = None

    def __init__(self):
        """
        Generate an authorized YouTube API client and S3 client
        """
        credentials = oauth2client.client.GoogleCredentials(
            settings.YT_ACCESS_TOKEN,
            settings.YT_CLIENT_ID,
            settings.YT_CLIENT_SECRET,
            settings.YT_REFRESH_TOKEN,
            None,
            'https://accounts.google.com/o/oauth2/token',
            None)
        authorization = credentials.authorize(httplib2.Http())
        credentials.refresh(authorization)
        self.client = build('youtube', 'v3', credentials=credentials)
        self.s3 = boto3.client('s3')

    def video_status(self, video_id):
        """
        Checks the  status of a video. 'processed' = ready for viewing.

        Args:
            video_id(str): YouTube video id

        Returns:
            str: status of the YouTube video

        """
        results = self.client.videos().list(
            part="status",
            id=video_id
        ).execute()
        return results['items'][0]['status']['uploadStatus']

    def list_captions(self, video_id):
        """
        List the captions available for a YouTube video

        Args:
            video_id(str): YouTube video id

        Returns:
            dict: List of captions in JSON format
        """
        results = self.client.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()

        return {item["snippet"]["language"]: item["id"] for item in results["items"]}

    def upload_caption(self, caption, video_id):
        """
        Upload a video caption to YouTube, inserting a new one or updating an existing one as necessary

        Args:
            caption(VideoSubtitle): The VideoSubtitle to upload to YouTube
            video_id(str): The YouTube ID of the video to associate the caption with.

        Returns:
            dict: YouTube API response
        """
        youtube_captions = self.list_captions(video_id)
        # YouTube API only seems to accept files or file-like objects, so download locally first
        with NamedTemporaryFile() as captionfile:
            self.s3.download_file(settings.VIDEO_S3_SUBTITLE_BUCKET, caption.s3_object_key, captionfile.name)
            media_body = MediaFileUpload(captionfile.name, mimetype='mime/vtt', chunksize=-1, resumable=True)
            if caption.language in youtube_captions:
                return self.update_caption(media_body, youtube_captions[caption.language])
            return self.insert_caption(caption, media_body, video_id)

    def insert_caption(self, caption, media_body, video_id):
        """
        Upload a new video caption to YouTube

        Args:
            caption(VideoSubtitle): The VideoSubtitle to upload to YouTube
            media_body(MediaFileUpload): The file containing the captions, in VTT format
            video_id(str): The YouTube ID of the video to associate the captions with.

        Returns:
            dict: YouTube API response

        """
        request = self.client.captions().insert(
            part="snippet",
            body=dict(
                snippet=dict(
                    videoId=video_id,
                    language=caption.language,
                    name=caption.language_name,
                    isDraft=False
                )
            ),
            media_body=media_body
        )
        return resumable_upload(request)

    def update_caption(self, media_body, caption_id):
        """
        Update an existing YouTube caption with a new file and return the JSON response.

        Args:
            media_body(MediaFileUpload): the video caption file to upload
            caption_id(str): The YouTube ID of the caption

        Returns:
            dict: YouTube API response
        """
        request = self.client.captions().update(
            part="snippet",
            body=dict(
                id=caption_id,
                snippet=dict(
                    isDraft=False
                )
            ),
            media_body=media_body
        )
        return resumable_upload(request)

    def delete_caption(self, caption_id):
        """
        Delete a caption from Youtube

        Args:
            caption_id(str): The ID of the YouTube caption

        Returns:
            int: 204 status code if successful
        """
        return self.client.captions().delete(id=caption_id).execute()

    def upload_video(self, video, privacy='unlisted'):
        """
        Transfer the video's original video file from S3 to YouTube.
        The YT account must be validated for videos > 15 minutes long:
        https://www.youtube.com/verify

        Args:
            video(Video): The Video object whose original source file will be uploaded'
            privacy(str): The privacy level to set the YouTube video to.

        Returns:
            dict: YouTube API response

        """
        videofile = video.original_video

        request_body = dict(
            snippet=dict(
                title=video.title,
                description=video.description
            ),
            status=dict(
                privacyStatus=privacy
            )
        )

        # YouTube API seems to insist on the video contents being available in their entirety before uploading,
        # so download from S3 into a temporary named file.
        with NamedTemporaryFile() as uploadfile:
            self.s3.download_file(settings.VIDEO_S3_BUCKET, videofile.s3_object_key, uploadfile.name)
            request = self.client.videos().insert(
                part=','.join(request_body.keys()),
                body=request_body,
                media_body=MediaFileUpload(uploadfile.name, mimetype='video/*', chunksize=-1, resumable=True)
            )

        response = resumable_upload(request)
        return response

    def delete_video(self, video_id):
        """
        Delete a video from YouTube

        Args:
            video_id(str): YouTube video id

        Returns:
            int: 204 status code if successful
        """
        return self.client.videos().delete(id=video_id).execute()
