"""Middleware for verifying a user has been invited to ON."""
# pylint: disable=no-self-use

import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

EXEMPT_URLS = [re.compile(settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [
        re.compile(exempt_url) for exempt_url in settings.LOGIN_EXEMPT_URLS]


class InviteMiddleware(object):
    """Checks that users have been invited to use ON."""
    def process_request(self, request):
        """Process request and ask for an invite code if needed."""
        # Find users that are logged in but haven't been verified
        if request.user.is_authenticated() and not request.user.invite_verified:
            path = request.path_info.lstrip('/')
            # Only check the invite for paths that require login
            if not any(m.match(path) for m in EXEMPT_URLS):
                redirect_to = '%s?next=%s' % (
                    reverse('enter_invite'), request.path_info)
                return HttpResponseRedirect(redirect_to)
