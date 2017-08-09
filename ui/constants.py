""" Statuses for Video objects """


class VideoStatus:
    """Simple class for possible video statuses"""
    CREATED = 'Created'
    UPLOADING = 'Uploading'
    UPLOAD_FAILED = 'Upload failed'
    TRANSCODING = 'Transcoding'
    TRANSCODE_FAILED_INTERNAL = 'Transcode failed internal error'
    TRANSCODE_FAILED_VIDEO = 'Transcode failed video error'
    COMPLETE = 'Complete'
    ERROR = 'Error'

    ALL_STATUSES = [
        CREATED,
        UPLOADING,
        UPLOAD_FAILED,
        TRANSCODING,
        TRANSCODE_FAILED_INTERNAL,
        TRANSCODE_FAILED_VIDEO,
        COMPLETE,
        ERROR,
    ]
