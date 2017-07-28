""" Statuses for Video objects """


class VideoStatus:
    """Simple class for possible video statuses"""
    CREATED = 'Created'
    UPLOADING = 'Uploading'
    UPLOAD_FAILED = 'Upload failed'
    TRANSCODING = 'Transcoding'
    TRANSCODE_FAILED = 'Transcode failed'
    COMPLETE = 'Complete'
    ERROR = 'Error'

    ALL_STATUSES = [CREATED, UPLOADING, UPLOAD_FAILED, TRANSCODING, TRANSCODE_FAILED, COMPLETE, ERROR]
