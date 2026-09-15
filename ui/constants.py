"""Statuses for Video objects"""

EDX_ADMIN_GROUP = "edX Course Admin"


class VideoStatus:
    """Simple class for possible video statuses"""

    CREATED = "Created"
    UPLOADING = "Uploading"
    UPLOAD_FAILED = "Upload failed"
    TRANSCODING = "Transcoding"
    TRANSCODE_FAILED_INTERNAL = "Transcode failed internal error"
    TRANSCODE_FAILED_VIDEO = "Transcode failed video error"
    RETRANSCODE_SCHEDULED = "Retranscode scheduled"
    RETRANSCODING = "Retranscoding"
    RETRANSCODE_FAILED = "Retranscode failed error"
    COMPLETE = "Complete"
    ERROR = "Error"

    ALL_STATUSES = [
        CREATED,
        UPLOADING,
        UPLOAD_FAILED,
        TRANSCODING,
        TRANSCODE_FAILED_INTERNAL,
        TRANSCODE_FAILED_VIDEO,
        RETRANSCODING,
        RETRANSCODE_FAILED,
        RETRANSCODE_SCHEDULED,
        COMPLETE,
        ERROR,
    ]


class YouTubeStatus:
    """Simple class for YouTube statuses"""

    UPLOADED = "uploaded"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PROCESSED = "processed"
    REJECTED = "rejected"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    RETRY = "retry"


class StreamSource:
    """Simple class for public collection streaming sources"""

    YOUTUBE = "Youtube"
    CLOUDFRONT = "Cloudfront"

    ALL_SOURCES = [
        YOUTUBE,
        CLOUDFRONT,
    ]


class DescriptionFormat:
    """
    How a Collection/Video `description` is encoded.

    Descriptions were plain text for most of this app's life, rendered escaped
    by React. They are now authored as rich text and rendered as markup, and the
    two cannot be told apart by looking at the value: a legacy description
    containing `<p>` may be markup an author pasted, or prose about HTML. So the
    format is recorded rather than guessed.

    `TEXT` is the default, which is what makes the switch safe for data already
    in the table: every existing row keeps being treated as plain text and
    rendered escaped, exactly as it was before rich text existed. Authors opt a
    description in one at a time (see ui.html.upgrade_description), and only a
    value written as rich text is ever rendered as markup.
    """

    TEXT = "text"
    HTML = "html"

    ALL_FORMATS = [
        TEXT,
        HTML,
    ]

    CHOICES = [
        (TEXT, "Plain text"),
        (HTML, "Rich text"),
    ]
