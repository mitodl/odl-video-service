""" techtv2ovs utils """
import logging
import re
import sys
import traceback
import os
from html import unescape
from io import BytesIO
from unicodedata import normalize

import MySQLdb
import boto3
import bonobo


from django.contrib.auth.models import User
from django.conf import settings
from django.utils.html import strip_tags
from dropbox import dropbox
from dropbox.exceptions import ApiError
from pycaption import CaptionConverter, SRTReader, WebVTTWriter

from techtv2ovs.constants import TTV_THUMB_BUCKET, TTV_VIDEO_BUCKET, ImportStatus
from techtv2ovs.models import TechTVCollection, TechTVVideo
from techtv2ovs.tasks import process_videofiles
from ui.constants import StreamSource

from ui.models import Collection, MoiraList, Video, VideoThumbnail, VideoSubtitle

# pylint: disable=attribute-defined-outside-init,broad-except,too-many-instance-attributes,too-many-arguments
from ui.utils import get_bucket


def mysql_query(query, params, connection):
    """
    Query MySQL and return results.

    Args:
        query (str): The query string
        params (tuple): parameters for the query string
        connection (MySQLdb.cursors.Cursor): A MySQL cursor

    Returns:
        tuple: Query results as a tuple of tuples
    """
    connection.execute(query, params)
    return connection.fetchall()


def moiralist_name(cid, name):
    """
    Return a formatted moira list name based on the name of a collection
    Based on TechTV / Ruby 'parameterize' function
    https://github.com/TechTV/TechTV/blob/master/app/models/collection/moira_controllable.rb#L76

    Args:
        cid (int): The ID of a TechTVCollection object
        name (str): The name of the TechTVCollection object

    Returns:
        str: The name of the moira list for the collection
    """
    # Replace certain special characters with dashes
    return 'techtv-{}-{}'.format(
        cid,
        re.sub(r'\-+', '-', (re.sub(r'[^A-Za-z0-9\-_]+', '', re.sub(r'[\s\'\.,\-\/\\@]+', '-', name))))[0:32].lower()
    )


def get_s3_videos(s3_prefix):
    """
    Get all the available S3 videofile objects for a TechTVVideo

    Args:
        s3_prefix (str): The TechTVVideo external id to use as the S3 bucket prefix to filter by

    Returns:
        list: A list of S3 objects
    """
    s3client = boto3.client('s3')
    meta = s3client.list_objects_v2(Bucket=TTV_VIDEO_BUCKET, Prefix=s3_prefix)
    return meta['Contents'] if 'Contents' in meta else []


def get_owner(email):
    """
    Get/create a user for emails ending with `@mit.edu`, otherwise return a default user

    Args:
        email (str): An email address

    Returns:
        User: A User object.
    """
    if email and email.endswith('@mit.edu'):
        user, _ = User.objects.get_or_create(username=email, defaults={
            'email': email
        })
        return user
    return User.objects.get(username=settings.LECTURE_CAPTURE_USER)


def remove_tags(txt):
    """
    Replace any HTML tags with spaces, HTML-encoded characters with unicode

    Args:
        txt (str): Text to remove HTML tags from.

    Returns:
        str: String with HTML tags/characters removed.
    """
    if not txt:
        return ''
    return normalize("NFKD", unescape(strip_tags(txt)))


class TechTVImporter:
    """
    Class for handling TechTV to OVS imports
    """

    def __init__(self, db_user=None, db_pw=None, db_name='techtv', db_host='127.0.0.1',
                 collections=None, aws=False, protected=1, output=sys.stdout, noyoutube=None, cloudfront=None):
        """
        Assign class properties based on kwargs

        Args:
            db_user (str): MySQL user
            db_pw (str): MySQL password
            db_name (str): MySQL database
            db_host (str): MySQL host
            collection (int): TechTV collection id
            aws (bool): Copy S3 files from TechTV to OVS
            protected (int): Process protected (1) or unprotected (0) collections
            output (object): Where to direct output to

        """
        self.db_user = db_user
        self.db_pw = db_pw
        self.db_name = db_name
        self.db_host = db_host
        self.collections = collections
        self.aws = aws
        self.protected = protected
        self.output = output
        self.noyoutube = noyoutube or []
        self.cloudfront = cloudfront or []

    def run(self):
        """
        Run the import
        """
        with MySQLdb.connect(
            user=self.db_user, password=self.db_pw, db=self.db_name, host=self.db_host
        ) as self.connection:
            bonobo.settings.LOGGING_LEVEL.set(logging.ERROR)
            bonobo.run(
                self.etl_graph()
            )

    def get_stream_source(self, collection_id):
        """
        Return the appropriate stream_source for transcoded videos
        Args:
            collection_id (int): The collection id

        Returns:
            str: where the video should be streamed from - Youtube, Cloudfront, or either one (None)
        """
        if self.protected == 1:
            return None
        if collection_id in self.noyoutube:
            return StreamSource.CLOUDFRONT
        if collection_id in self.cloudfront:
            return None
        return StreamSource.YOUTUBE

    def process_thumbs(self, ttv_video):
        """
        Copy over all 'jumbo' thumbnails from TechTV to OVS buckets for a TechTVVideo.
        Create a VideoThumbnail object for each.

        Args:
            ttv_video (TechTVVideo): The TechTVVideo to process
        """
        ttv_video.thumbnail_status = ImportStatus.CREATED
        s3client = boto3.client('s3')
        s3list = s3client.list_objects_v2(Bucket=TTV_THUMB_BUCKET, Prefix=ttv_video.external_id)
        if 'Contents' not in s3list or not s3list['Contents']:
            ttv_video.thumbnail_status = ImportStatus.MISSING
            ttv_video.save()
            return
        user_list = [thumb for thumb in s3list['Contents'] if '{}/jumbo'.format(ttv_video.ttv_id) in thumb['Key']]
        default_list = [thumb for thumb in s3list['Contents'] if 'thumbnails/jumbo' in thumb['Key']]
        idx = 0
        for thumb in user_list + default_list:
            new_key = thumb['Key'].split('/')[-1].replace('jumbo', str(idx))
            try:
                src = {'Bucket': TTV_THUMB_BUCKET, 'Key': thumb['Key']}
                dst_bucket = settings.VIDEO_S3_THUMBNAIL_BUCKET
                dst_key = 'thumbnails/techtv/{}/{}'.format(ttv_video.video.hexkey, new_key)

                if self.aws:
                    s3client.copy(src, dst_bucket, dst_key)

                VideoThumbnail.objects.get_or_create(s3_object_key=dst_key, defaults={
                    'bucket_name': dst_bucket,
                    'video': ttv_video.video
                })
                idx += 1
            except Exception as exc:
                self.output.write("Error: thumbnail {} for ttv video {}".format(src['Key'], ttv_video.ttv_id))
                ttv_video.status = ImportStatus.ERROR
                ttv_video.thumbnail_status = ImportStatus.ERROR
                ttv_video.errors += '{}:{}\n\n'.format(str(exc), traceback.format_exc())

        if ttv_video.thumbnail_status != ImportStatus.ERROR:
            ttv_video.thumbnail_status = ImportStatus.COMPLETE
        ttv_video.save()

    def process_captions(self, ttv_video):
        """
        Copy over any caption files for a TechTVVideo from Dropbox to S3.
        Create a VideoSubtitle object for each.

        Args:
            ttv_video (TechTVVideo): The TechTVVideo object to process
        """
        ttv_video.subtitle_status = ImportStatus.CREATED
        captions = [caption[0] for caption in mysql_query(
            'SELECT srt_file_file_name from closed_caption_files where video_id = %s', [ttv_video.ttv_id],
            self.connection
        )]
        for caption in captions:
            try:
                basename, _ = os.path.splitext(caption)
                dbx = dropbox.Dropbox(os.getenv('DROPBOX_TOKEN'))
                dbx_folder = os.getenv('DROPBOX_FOLDER')
                try:
                    _, response = dbx.files_download(os.path.join(dbx_folder, caption))
                except ApiError:
                    _, response = dbx.files_download(
                        os.path.join(dbx_folder, caption.replace('_', ' '))
                    )
                srt_bytes = BytesIO(response.content)
                bucket = get_bucket(settings.VIDEO_S3_SUBTITLE_BUCKET)
                bucket.upload_fileobj(
                    Fileobj=srt_bytes,
                    Key='subtitles/techtv/{}/{}'.format(ttv_video.video.hexkey, caption)
                )
                vtt_key = 'subtitles/techtv/{}/{}.vtt'.format(ttv_video.video.hexkey, basename)
                converter = CaptionConverter()
                converter.read(response.content.decode('utf-8').replace("\ufeff1", "1"), SRTReader())
                vtt_content = converter.write(WebVTTWriter())

                bucket.upload_fileobj(
                    Fileobj=BytesIO(vtt_content.encode('utf-8')),
                    Key=vtt_key
                )
                VideoSubtitle.objects.get_or_create(s3_object_key=vtt_key, defaults={
                    'video': ttv_video.video
                })
            except Exception as exc:
                self.output.write("Error: caption file {} for ttv video {}".format(caption, ttv_video.ttv_id))
                ttv_video.status = ImportStatus.ERROR
                ttv_video.subtitle_status = ImportStatus.ERROR
                ttv_video.errors += '{}:{}\n\n'.format(str(exc), traceback.format_exc())
        if ttv_video.subtitle_status != ImportStatus.ERROR:
            ttv_video.subtitle_status = ImportStatus.COMPLETE
        ttv_video.save()

    def process_files(self, ttv_video, s3videos):
        """
        Import videofiles, thumbnails, and captions for a TechTVVideo.

        Args:
            ttv_video (TechTVVideo): The TechTVVideo object to process
            s3videos (list): List of video file S3 objects
        """
        try:
            self.process_thumbs(ttv_video)
            self.process_captions(ttv_video)
            process_videofiles.delay(ttv_video.id, s3videos, self.aws)
        except Exception as exc:
            ttv_video.status = ImportStatus.ERROR
            ttv_video.errors += '{}:{}\n\n'.format(str(exc), traceback.format_exc())
            ttv_video.save()

    def process_videos(self, ttvcollection):
        """
        Process all the videos for a TechTV Collection

        Args:
            ttvcollection (TechTVCollection): a TechTVCollection object
        """
        video_query = (
            'SELECT v.id, v.title, v.description, v.external_id, v.private, v.private_token '
            'from videos v inner join collection_videos cv on cv.video_id = v.id where cv.collection_id = %s '
            'and v.status = \'approved\' AND v.file_restored = 1 AND v.locked=0;'
        )
        videos = mysql_query(video_query, (ttvcollection.id,), self.connection)
        for v_id, v_title, v_description, external_id, private, token in videos:
            self.output.write('Processing video: {}'.format(v_title))
            ttvvideo, _ = TechTVVideo.objects.update_or_create(
                ttv_id=v_id,
                ttv_collection=ttvcollection,
                defaults={
                    'title': v_title,
                    'description': v_description,
                    'external_id': external_id,
                    'private': True if private == 1 else False,
                    'private_token': token
                }
            )
            s3videos = get_s3_videos(external_id)
            if not s3videos:
                ttvvideo.status = ImportStatus.MISSING
                ttvvideo.videofile_status = ImportStatus.MISSING
                ttvvideo.save()
                continue
            if not ttvvideo.video:
                ttvvideo.video = Video.objects.create(
                    collection=ttvcollection.collection,
                    title=v_title,
                    description=remove_tags(v_description),
                    source_url="http://techtv.mit.edu/videos/",
                    is_private=ttvvideo.private,
                    is_public=(self.protected == 0)
                )
            ttvvideo.status = ImportStatus.CREATED
            ttvvideo.save()
            self.process_files(ttvvideo, s3videos)

    def process_collection(self, cid, name, description, email):
        """
        Iterate over every TechTV collection

        Args:
            cid (int): TechTV collection ID
            name (str): TechTV collection name
            description (str): TechTV collection description
            email (str): TechTV collection owner's email address
        """
        ttvcollection, _ = TechTVCollection.objects.update_or_create(id=cid, defaults={
            'name': name,
            'description': description,
            'owner_email': email,
        })
        self.output.write('Processing collection: {}'.format(name))
        stream_source = self.get_stream_source(cid)
        if not ttvcollection.collection:
            view_list, _ = MoiraList.objects.get_or_create(name=moiralist_name(cid, name))
            admin_list, _ = MoiraList.objects.get_or_create(name='{}-owner'.format(view_list.name))
            ovs_collection = Collection.objects.create(
                title=name,
                description=remove_tags(description),
                owner=get_owner(email),
                stream_source=stream_source
            )
            ovs_collection.admin_lists = [admin_list]
            ovs_collection.view_lists = [view_list]
            ovs_collection.save()
            ttvcollection.collection = ovs_collection
            ttvcollection.save()
        elif ttvcollection.collection.stream_source != stream_source:
            ttvcollection.collection.stream_source = stream_source
            ttvcollection.collection.save()
        self.process_videos(ttvcollection)

    def extract_collections(self):
        """
        Yield TechTV collections from MySQL

        Yields:
            tuple: Tuple of database rows (as tuples) from the collections table

        """
        collection_query = (
            'SELECT DISTINCT c.id, c.name, c.description, u.email FROM collections c '
            'INNER JOIN collection_videos cv ON c.id = cv.collection_id '
            'INNER JOIN videos v on v.id = cv.video_id '
            'LEFT JOIN users u ON c.user_id = u.id '
            'WHERE v.status = \'approved\' and v.file_restored = 1 AND v.locked = 0 AND c.protected = %s'
        )
        params = [self.protected]
        if self.collections:
            collection_query += " and c.id in ({})".format(','.join('%s' for _ in self.collections))
            params.extend(self.collections)

        collections = mysql_query(
            collection_query,
            tuple(params),
            self.connection
        )
        yield from collections

    def etl_graph(self):
        """
        This function builds the Bonobo ETL graph that needs to be executed.

        Returns:
             bonobo.Graph: Graph of ETL functions

        """
        graph = bonobo.Graph()
        graph.add_chain(self.extract_collections, self.process_collection)
        return graph
