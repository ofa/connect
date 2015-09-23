"""Middleware to handle IP addresses in the app"""
from ipware.ip import get_real_ip


class SetCorrectIPMiddleware(object):
    """Make sure that django has the correct IP even if there is a proxy/CDN"""
    # pylint: disable=no-self-use
    def process_request(self, request):
        """Process a request"""
        ip_address = get_real_ip(request)
        if ip_address is not None:
            request.META["HTTP_X_FORWARDED_FOR"] = ip_address
            request.META["REMOTE_ADDR"] = ip_address
