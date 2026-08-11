"""Custom middleware for the odl_video project"""


class RobotsTagMiddleware:
    """Add an X-Robots-Tag header to every response so search engines are
    told not to index any page, regardless of which template (if any)
    rendered it. This covers views that don't extend base.html, such as
    the Django admin and DRF browsable API (see mitodl/hq#12798).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
