"""Custom exceptions"""


class TranscodeTargetDoesNotExist(Exception):
    """Custom exception to be used when a video does not exist for a transcode task"""


class TransferError(Exception):
    """Raised when the source returns an unexpected response and cannot be transferred."""


class TransferAbortedByCaller(Exception):
    """
    Raised by a range-fetcher to stop a transfer cleanly without aborting the multipart upload.

    Used when the caller detects that it should stop (e.g. it has lost lock ownership) but
    the multipart upload state should be preserved so another worker can resume it.
    """
