"""Tests for utils/auth_backends.py"""
# pylint: disable=protected-access
from django.test import TestCase
from mock import patch, Mock

from open_connect.connect_core.utils.auth_backends import (
    CachedModelAuthBackend
)
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class TestCachedModelAuthBackend(ConnectTestMixin, TestCase):
    """Tests for CachedModelAuthBackend"""
    def setUp(self):
        """Setup tests for CachedModelAuthBackend"""
        cache_patcher = patch(
            'open_connect.connect_core.utils.auth_backends.cache')
        self.mockcache = cache_patcher.start()
        self.addCleanup(cache_patcher.stop)

    def test_anonymous(self):
        """Test for an anonymous user object"""
        backend = CachedModelAuthBackend()
        mock_user = Mock()
        mock_user.is_anonymous.return_value = True

        result = backend.get_all_permissions(mock_user)
        self.assertEqual(result, set())
        self.assertFalse(self.mockcache.get.called)

    def test_has_perm_cache(self):
        """Test where a user object already has a permission cache"""
        user = self.create_user()
        demo_cache = Mock()
        setattr(user, '_perm_cache', demo_cache)
        backend = CachedModelAuthBackend()

        result = backend.get_all_permissions(user)
        self.assertEqual(result, demo_cache)
        self.assertFalse(self.mockcache.get.called)

    def test_empty_cache(self):
        """Test where the cache does not contain permissions"""
        self.mockcache.get.return_value = None

        user = self.create_user()
        self.add_perm(user, 'can_moderate_all_messages', 'accounts', 'user')

        backend = CachedModelAuthBackend()
        result = backend.get_all_permissions(user)

        self.mockcache.get(user.cache_key + '_permissions')
        self.mockcache.set.assert_called_once_with(
            user.cache_key + '_permissions',
            result,
            1800
        )
        self.assertEqual(user._perm_cache, result)
        self.assertIn(u'accounts.can_moderate_all_messages', result)

    def test_full_cache(self):
        """Test where the cache is full and should be returned"""
        demo_result = Mock()
        self.mockcache.get.return_value = demo_result

        user = self.create_user()
        backend = CachedModelAuthBackend()
        result = backend.get_all_permissions(user)

        self.mockcache.get.assert_called_once_with(
            user.cache_key + '_permissions')
        self.assertEqual(user._perm_cache, demo_result)
        self.assertEqual(result, demo_result)
