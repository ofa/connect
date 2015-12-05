"""Middleware for verifying a user has accepted the ToS and UCoC."""
# pylint: disable=no-self-use
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

EXEMPT_URLS = [re.compile(settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [
        re.compile(exempt_url) for exempt_url in settings.LOGIN_EXEMPT_URLS]


class AcceptTermsAndConductMiddleware(object):
    """Checks that users have accepted terms and conduct agreements."""
    def process_request(self, request):
        """Process request and ask for an invite code if needed."""
        # Find users that are logged in but haven't been verified
        user = request.user
        if user.is_authenticated() and not request.is_ajax():
            if user.tos_accepted_at and user.ucoc_accepted_at:
                return
            path = request.path_info.lstrip('/')
            # Only check the invite for paths that require login
            if not any(m.match(path) for m in EXEMPT_URLS):
                redirect_to = '{url}?next={next}'.format(
                    url=reverse('accept_terms_and_conduct'),
                    next=request.path_info
                )
                return HttpResponseRedirect(redirect_to)
