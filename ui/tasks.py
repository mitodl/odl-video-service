"""
ui celery tasks
"""
from celery import shared_task

from ui.util import get_bucket


@shared_task(bind=True)
def delete_s3_objects(self, bucket_name, key, as_filter=False):  # pylint:disable=unused-argument
    """
    Delete objects from an S3 bucket

    Args:
        bucket_name(str): Name of S3 bucket
        key(str): S3 key or key prefix
        as_filter(bool): Filter the bucket by the key
    """
    bucket = get_bucket(bucket_name)
    if not as_filter:
        bucket.delete_objects(Delete={'Objects': [{'Key': key}]})
    else:
        for obj in bucket.objects.filter(Prefix=key):
            obj.delete()
