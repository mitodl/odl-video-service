""" Statuses for Video objects """


class VideoStatus:
    """Simple class for possible video statuses"""
    CREATED = 'Created'
    UPLOADING = 'Uploading'
    UPLOAD_FAILED = 'Upload failed'
    TRANSCODING = 'Transcoding'
    TRANSCODE_FAILED_INTERNAL = 'Transcode failed internal error'
    TRANSCODE_FAILED_VIDEO = 'Transcode failed video error'
    RETRANSCODING = 'Retranscoding'
    RETRANSCODE_FAILED = "Retranscode failed error"
    COMPLETE = 'Complete'
    ERROR = 'Error'

    ALL_STATUSES = [
        CREATED,
        UPLOADING,
        UPLOAD_FAILED,
        TRANSCODING,
        TRANSCODE_FAILED_INTERNAL,
        TRANSCODE_FAILED_VIDEO,
        RETRANSCODING,
        COMPLETE,
        ERROR,
    ]


class YouTubeStatus:
    """Simple class for YouTube statuses"""
    UPLOADED = 'uploaded'
    UPLOADING = 'uploading'
    PROCESSING = 'processing'
    PROCESSED = 'processed'
    REJECTED = 'rejected'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'
    RETRY = 'retry'


class StreamSource:
    """ Simple class for public collection streaming sources """
    YOUTUBE = 'Youtube'
    CLOUDFRONT = 'Cloudfront'

    ALL_SOURCES = [
        YOUTUBE,
        CLOUDFRONT,
    ]
