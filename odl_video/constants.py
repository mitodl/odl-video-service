"""App constants"""

DEFAULT_EDX_VIDEO_API_PATH = "/api/val/v0/videos/"
EDX_VIDEO_IMAGE_API_PATH = "/api/contentstore/v0/videos/images/"
# A course-v1 key with no characters that could change a URL's path, query or fragment
EDX_COURSE_KEY_PATTERN = r"^course-v1:[\w.~-]+\+[\w.~-]+\+[\w.~-]+$"

# Studio rejects video images outside these limits (edx-platform settings VIDEO_IMAGE_*)
EDX_VIDEO_IMAGE_MIN_WIDTH = 640
EDX_VIDEO_IMAGE_MIN_HEIGHT = 360
# edX's recommended resolution; padded copies are scaled down to it
EDX_VIDEO_IMAGE_MAX_WIDTH = 1280
EDX_VIDEO_IMAGE_MAX_HEIGHT = 720
EDX_VIDEO_IMAGE_ASPECT_RATIO = 16 / 9
EDX_VIDEO_IMAGE_ASPECT_RATIO_ERROR_MARGIN = 0.1
EDX_VIDEO_IMAGE_MIN_BYTES = 2 * 1024
EDX_VIDEO_IMAGE_MAX_BYTES = 2 * 1024 * 1024
