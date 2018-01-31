"""
Video encoding names
"""


class EncodingNames:
    """Simple class to hold encoding names"""
    ORIGINAL = 'original'
    HLS = 'HLS'
    SMALL = 'small'
    BASIC = 'basic'
    MEDIUM = 'medium'
    LARGE = 'large'
    HD = 'HD'
    MP4 = [HD, LARGE, MEDIUM, BASIC, SMALL]
