"""Tests for login_required middleware."""
# pylint: disable=invalid-name
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from django.contrib.auth import get_user_model


USER_MODEL = get_user_model()


class LoginRequiredMiddlewareTest(TestCase):
    """Tests for login_required middleware."""
    def setUp(self):
        """Setup the LoginRequiredMiddlewareTest TestCase"""
        self.user = USER_MODEL.objects.create_superuser(
            'test@razzmatazz.local', 'greentea')

    def test_login(self):
        """Assert that a user can login."""
        self.assertTrue(
            self.client.login(
                username='test@razzmatazz.local', password='greentea'))

    def test_login_required(self):
        """Test that login is required for different kinds of requests."""
        def check_url(url_data):
            """Check a url and assert that it provides the correct response."""
            open_func = getattr(self.client, url_data.get('method', 'get'))
            if 'args' in url_data:
                response = open_func(reverse(url_data['url'],
                                             args=url_data.get('args')))
            elif 'kwargs' in url_data:
                response = open_func(reverse(url_data['url'],
                                             kwargs=url_data.get('kwargs')))
            else:
                response = open_func(reverse(url_data['url']))
            self.assertEqual(
                response.status_code, 302, 'URL: %s' % url_data['url'])

        urllist = [
            {'url': 'create_message'},
            {'url': 'thread_details_json', 'kwargs': {'pk': 1}},
            {'url': 'messages'},
            {'url': 'update_subscriptions', 'method': 'post'},
            {'url': 'user_profile'},
        ]
        for url in urllist:
            yield check_url, url

    def test_root_is_not_required(self):
        """Root of the application should be valid."""
        client = Client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'welcome.html')
