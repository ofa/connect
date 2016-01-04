"""Tests for login_required middleware."""
# pylint: disable=invalid-name
import json
import re

from mock import patch

from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django.test.client import Client

from open_connect.connect_core.utils.basetests import ConnectTestMixin


class LoginRequiredMiddlewareTest(ConnectTestMixin, TestCase):
    """Tests for login_required middleware."""

    @override_settings(LOGIN_URL='http://domain.example/login/backend/')
    def test_redirect(self):
        """Test that unauthenticated requests redirect to login flow"""
        unauthenticated_client = Client()

        mock_exempt_urls = [
            re.compile(r'^$'),
        ]
        with patch(
            'open_connect.middleware.login_required.EXEMPT_URLS',
            mock_exempt_urls):

            response = unauthenticated_client.get('/abcd/123/test')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                'http://domain.example/login/backend/?next=/abcd/123/test',
                response.url)

    @override_settings(LOGIN_URL='http://domain.example/login/backend/')
    def test_exempt_url(self):
        """Test the Exempt-URL Regex"""
        unauthenticated_client = Client()

        # There is no trivial way to mock the `LOGIN_EXEMPT_URL` setting here,
        # so we'll need to ovverride the calculated result of the setting and
        # patch that.
        mock_exempt_urls = [
            re.compile(r'^test1/wildcard/*'),
            re.compile(r'^test2/absolute/$')
        ]
        with patch(
            'open_connect.middleware.login_required.EXEMPT_URLS',
            mock_exempt_urls):

            # Test a wildcard regex exempt url. This will return a 404 instead
            # of redirect to the login flow
            valid_wildcard = unauthenticated_client.get('/test1/wildcard/a')
            self.assertEqual(valid_wildcard.status_code, 404)

            # Test an absolute regex exempt url. This will also return a 404
            valid_absolute = unauthenticated_client.get('/test2/absolute/')
            self.assertEqual(valid_absolute.status_code, 404)

            # Test a URL that is not exempt. This will 302 through the login
            # flow.
            unexempt_url = unauthenticated_client.get('/test3/not_exempt')
            self.assertEqual(unexempt_url.status_code, 302)
            self.assertEqual(
                'http://domain.example/login/backend/?next=/test3/not_exempt',
                unexempt_url.url)

    def test_ajax_request(self):
        """Test an unauthented AJAX request to search for a 400"""
        client = Client()
        response = client.get(
            reverse('create_message'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertDictItemsEqualUnordered(
            response_data,
            {
                'success': False,
                'errors': [
                    'You Must Be Logged In'
                ]
            }
        )

    def test_no_cache_header(self):
        """Test that responses contain all the relevant no-cache headers"""
        client = Client()
        response = client.get(reverse('create_message'))
        self.assertEqual(response.status_code, 302)

        self.assertIn('proxy-revalidate', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('max-age=0', response['Cache-Control'])
        self.assertIn('no-cache', response['Cache-Control'])
        self.assertIn('must-revalidate', response['Cache-Control'])
        self.assertIn('s-maxage=0', response['Cache-Control'])

    def test_root_is_not_required(self):
        """Root of the application should be valid."""
        client = Client()
        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'welcome.html')
