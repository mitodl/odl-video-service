""" TechTV constants """

TTV_VIDEO_BUCKET = "ttv_videos"
TTV_THUMB_BUCKET = "ttv_static"


class ImportStatus:
    """Simple class for possible video statuses"""

    CREATED = "Created"
    COMPLETE = "Complete"
    ERROR = "Error"
    MISSING = "Missing"

    ALL_STATUSES = [CREATED, COMPLETE, ERROR, MISSING]
