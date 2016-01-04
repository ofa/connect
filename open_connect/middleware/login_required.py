"""Middleware for redirecting unauthenticated users."""
# pylint: disable=no-self-use

import re
import json

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.views.decorators.cache import patch_cache_control


EXEMPT_URLS = [re.compile(settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [
        re.compile(exempt_url) for exempt_url in settings.LOGIN_EXEMPT_URLS]


class LoginRequiredMiddleware(object):
    """
    Middleware that requires a user to be authenticated to view any page other
    than LOGIN_URL. Exemptions to this requirement can optionally be specified
    in settings via a list of regular expressions in LOGIN_EXEMPT_URLS (which
    you can copy from your urls.py).

    Requires authentication middleware and template context processors to be
    loaded. You'll get an error if they aren't.
    """
    def process_request(self, request):
        """Process request and redirect user if they're unauthenticated."""
        if not request.user.is_authenticated():
            path = request.path_info.lstrip('/')
            if path == '':
                return
            if not any(m.match(path) for m in EXEMPT_URLS):
                if request.is_ajax():
                    # For AJAX requests, return a 400 (which will trigger
                    # jquery's ajax error functionality) and include the error
                    # in a way consistent with the rest of Connect. This is to
                    # prevent AJAX requests from ever being sent through the
                    # login flow (which can cause problems.)
                    response = HttpResponseBadRequest(
                        json.dumps({
                            'success': False,
                            'errors': [
                                'You Must Be Logged In',
                            ]
                        }),
                        content_type='application/json'
                    )
                else:
                    redirect_to = '%s?next=%s' % (settings.LOGIN_URL,
                                                  request.path_info)
                    response = HttpResponseRedirect(redirect_to)

                # Break the client-side cache on all possible browsers on all
                # protocols.
                patch_cache_control(
                    response, no_cache=True, no_store=True,
                    must_revalidate=True, max_age=0, private=True,
                    proxy_revalidate=True, s_maxage=0)
                return response
