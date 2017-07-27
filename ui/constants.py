""" Statuses for Video objects """


class VideoStatus:
    """Simple class for possible video statuses"""
    UPLOADING = 'Uploading'
    UPLOAD_FAILED = 'Upload failed'
    TRANSCODING = 'Transcoding'
    TRANSCODE_FAILED = 'Transcode failed'
    COMPLETE = 'Complete'
    ERROR = 'Error'
