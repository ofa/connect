"""Middleware for storing details about a user's visit."""
from open_connect.accounts.models import Visit


class VisitTrackingMiddleware(object):
    """Stores details about a user's visits."""
    # pylint: disable=no-self-use
    def process_response(self, request, response):
        """Store visit data if this is the first visit from user in 24 hours."""

        if not hasattr(request, 'user'):
            return response

        is_tracked = request.COOKIES.get('visit_logged')
        if is_tracked or not request.user.is_authenticated():
            return response
        Visit.objects.create(
            user=request.user,
            ip_address=request.META.get(
                'HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')
            ),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        response.set_cookie('visit_logged', value='1', max_age=86400)

        return response
