"""
Video encoding names
"""


class EncodingNames:
    """Simple class to hold encoding names"""

    ORIGINAL = "original"
    HLS = "HLS"
    SMALL = "small"
    BASIC = "basic"
    MEDIUM = "medium"
    LARGE = "large"
    HD = "HD"
    DESKTOP_MP4 = "desktop_mp4"
    MP4 = [HD, LARGE, MEDIUM, BASIC, SMALL]
