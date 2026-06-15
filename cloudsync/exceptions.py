"""Custom exceptions"""


class TranscodeTargetDoesNotExist(Exception):
    """Custom exception to be used when a video does not exist for a transcode task"""


class TransferError(Exception):
    """Raised when the source returns an unexpected response and cannot be transferred."""
