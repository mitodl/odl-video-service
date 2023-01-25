""" Constants for mail """
from ui.constants import VideoStatus

EMAIL_SUCCESS = "success"
EMAIL_INVALID_FORMAT = "invalid_format_error"
EMAIL_OTHER_ERROR = "other_error"

STATUS_TO_NOTIFICATION = {
    VideoStatus.COMPLETE: EMAIL_SUCCESS,
    VideoStatus.TRANSCODE_FAILED_INTERNAL: EMAIL_OTHER_ERROR,
    VideoStatus.TRANSCODE_FAILED_VIDEO: EMAIL_INVALID_FORMAT,
    VideoStatus.UPLOAD_FAILED: EMAIL_OTHER_ERROR,
}

STATUSES_THAT_TRIGGER_DEBUG_EMAIL = set(
    [
        VideoStatus.TRANSCODE_FAILED_INTERNAL,
        VideoStatus.UPLOAD_FAILED,
    ]
)
