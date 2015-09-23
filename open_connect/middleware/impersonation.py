"""Middleware to impersonate another user."""
from django.contrib.auth import get_user_model


class ImpersonationMiddleware(object):
    """Middleware to impersonate another user."""
    # pylint: disable=no-self-use
    def process_request(self, request):
        """Set the request user to user to impersonate."""
        # pylint: disable=invalid-name
        User = get_user_model()
        impersonate_id = request.session.get('impersonate_id', None)
        request.user.impersonating = False
        if not impersonate_id:
            return
        if not request.user.can_impersonate():
            return
        try:
            user = User.objects.get(pk=impersonate_id)
        except User.DoesNotExist:
            return
        else:
            request.user = user
            request.user.impersonating = True
