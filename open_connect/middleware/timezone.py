"""Middleware for setting a user's timezone."""

from django.utils import timezone
import pytz


class TimezoneMiddleware(object):
    """Middleware for setting a user's timezone."""
    # pylint: disable=no-self-use
    def process_request(self, request):
        """Process the request and set the timezone."""
        if request.user.is_authenticated():
            if request.user.timezone:
                timezone.activate(pytz.timezone(request.user.timezone))
