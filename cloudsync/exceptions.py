""" Custom exceptions"""


class VideoFilenameError(ValueError):
    """Custom exception to be used when a video filename can't be matched to a regex pattern"""


class TranscodeTargetDoesNotExist(Exception):
    """Custom exception to be used when a video does not exist for a transcode task"""
