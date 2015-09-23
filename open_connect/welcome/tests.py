"""Tests for welcome app."""
# pylint: disable=invalid-name

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, resolve
from django.test import SimpleTestCase, RequestFactory
from mock import Mock

from open_connect.welcome.views import WelcomeView

WELCOME_URL = reverse('welcome')

USER_MODEL = get_user_model()


class WelcomeViewTest(SimpleTestCase):
    """Tests for the welcome application."""
    def test_redirects_to_threads_if_authenticated_and_user_has_groups(self):
        """User should be sent to threads if they have subscriptions."""
        factory = RequestFactory()
        request = factory.get('/')
        user = Mock()
        user.is_authenticated.return_value = True
        user.groups.all.return_value.exists.return_value = True
        request.user = user
        view = WelcomeView()
        result = view.get(request)
        self.assertEqual(result['Location'], reverse('threads'))

    def test_redirects_to_threads_if_authenticated_and_user_has_no_groups(self):
        """User should be sent to groups if they aren't subscribed to any."""
        factory = RequestFactory()
        request = factory.get('/')
        user = Mock()
        user.is_authenticated.return_value = True
        user.groups.all.return_value.exists.return_value = False
        request.user = user
        view = WelcomeView()
        result = view.get(request)
        self.assertEqual(result['Location'], reverse('groups'))

    def test_displays_welcome_if_not_logged_in(self):
        """User should see welcome page if they aren't authenticated."""
        factory = RequestFactory()
        request = factory.get('/')
        user = Mock()
        user.is_authenticated.return_value = False
        request.user = user
        view = WelcomeView()
        view.request = request
        result = view.get(request)
        self.assertEqual(result.template_name, ['welcome.html'])

    def test_root_resolves_to_welcome(self):
        """Getting / should resolve to WelcomeView."""
        result = resolve('/')
        self.assertEqual(result.func.__name__, 'WelcomeView')
