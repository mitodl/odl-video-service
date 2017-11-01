from django.utils.deprecation import MiddlewareMixin
import logging


log = logging.getLogger(__name__)
META_KEYS = [
    'REQUEST_METHOD',
    'REQUEST_URI',
    'PATH_INFO',
]
META_HTTP_IGNORE = [
    'HTTP_CONNECTION',
    'HTTP_CACHE_CONTROL',
    'HTTP_USER_AGENT',
    'HTTP_ACCEPT',
    'HTTP_ACCEPT_ENCODING',
    'HTTP_ACCEPT_LANGUAGE',
]
META_HTTP_PREFIX = 'HTTP_'

class DebuggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        log.warning('\n\n################# INCOMING REQUEST #################\n##### request.META')
        for k, v in request.META.items():
            if k in META_KEYS or (k.startswith(META_HTTP_PREFIX) and k not in META_HTTP_IGNORE):
                log.warning('%s: %s', k, v)
        if request.COOKIES:
            log.warning('\n\n##### request.COOKIES')
            for k, v in request.COOKIES.items():
                log.warning('%s: %s', k, v)
        # if request.POST:
        #     log.warning('\nrequest.POST')
        #     for k, v in request.POST.items():
        #         log.warning('%s: %s', k, v)
        log.warning('\n\n\n')
