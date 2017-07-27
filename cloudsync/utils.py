"""Utility classes/methods for cloudsync"""
from uuid import uuid4

from dj_elastictranscoder.models import EncodeJob
from dj_elastictranscoder.transcoder import Transcoder
from django.contrib.contenttypes.models import ContentType


class VideoTranscoder(Transcoder):
    """
    Customized version of dj_elastictranscoder.transcoder
    """
    def create_job_for_object(self, obj):
        """
        Create an EncodeJob with the same message output as the Transcoder message

        Args:
            obj(Video): Video to create a job for

        Returns:
            EncodeJob object

        """
        content_type = ContentType.objects.get_for_model(obj)
        uuid = str(uuid4())
        if not hasattr(self, 'message'):
            self.message = {'Job': {'Status': 'Error', 'Id': uuid}}  # pylint:disable=attribute-defined-outside-init
        job = EncodeJob()
        job.id = self.message['Job']['Id'] if 'Job' in self.message else uuid
        job.message = self.message
        job.content_type = content_type
        job.object_id = obj.pk
        job.save()
        return job
