"""Tests for context_processors.active_url_name."""
# pylint: disable=invalid-name
from django.core.urlresolvers import ResolverMatch, Resolver404
from django.test import RequestFactory, TestCase
from mock import patch

from open_connect.context_processors.active_url_name import add_active_url_name


def get_resolver_match(url_name='dr_pepper', app_name='sodas'):
    """Resolve a url back to a view."""
    return ResolverMatch(None, [], {}, url_name=url_name, app_name=app_name)


class TestActiveURLName(TestCase):
    """Tests for context_processors.active_url_name."""
    def setUp(self):
        """Setup the TestActiveURLName TestCase"""
        self.request = RequestFactory()
        self.request.path_info = '/some_url/'

    @patch('open_connect.context_processors.active_url_name.resolve')
    def test_active_url_name_added_to_context(self, mock):
        """Test that active_url_name is added to context."""
        mock.return_value = get_resolver_match()
        context = add_active_url_name(self.request)
        self.assertEqual(context.get('active_url_name', ''), 'dr_pepper')
        self.assertEqual(context.get('app_name', ''), 'sodas')

    @patch('open_connect.context_processors.active_url_name.resolve')
    def test_app_name_added_to_context(self, mock):
        """Test that app_name is added to the context."""
        mock.return_value = get_resolver_match()
        context = add_active_url_name(self.request)
        self.assertEqual(context.get('active_url_name', ''), 'dr_pepper')
        self.assertEqual(context.get('app_name', ''), 'sodas')

    @patch('open_connect.context_processors.active_url_name.resolve')
    def test_app_name_is_none_if_not_set(self, mock):
        """Test that app_name is None if it's not set."""
        mock.return_value = get_resolver_match(app_name=None)
        context = add_active_url_name(self.request)
        self.assertEqual(context.get('active_url_name', ''), 'dr_pepper')
        self.assertEqual(context.get('app_name'), None)

    @patch('open_connect.context_processors.active_url_name.resolve')
    def test_returns_nothing_with_error(self, mock):
        """Test that when a resolve fails an empty context is returned"""
        mock.side_effect = Resolver404()
        context = add_active_url_name(self.request)
        self.assertNotIn('active_url_name', context)
        self.assertNotIn('app_name', context)
