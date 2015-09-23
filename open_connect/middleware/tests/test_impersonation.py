"""Tests for impersonation middleware."""
# pylint: disable=invalid-name
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory

from open_connect.middleware.impersonation import ImpersonationMiddleware


User = get_user_model()


class ImpersonationMiddlewareTest(TestCase):
    """Tests for the impersonation middleware."""
    def setUp(self):
        """Setup the ImpersonationMiddlewareTest TestCase"""
        self.user = User.objects.create_user(
            username='impersonate@me.local', password='abc')
        self.admin = User.objects.create_user(
            username='admin@dj.local', password='abc')
        self.client.post(
            reverse('login'),
            {'username': 'admin@dj.local', 'password': 'abc'}
        )
        self.request_factory = RequestFactory()

    def test_process_request_admin_has_permission(self):
        """A user with permission should be able to impersonate another user."""
        # Make sure user has can_impersonate permission
        permission = Permission.objects.get_by_natural_key(
            'can_impersonate', 'accounts', 'user')
        self.admin.user_permissions.add(permission)
        self.admin.save()
        self.assertTrue(self.admin.has_perm('accounts.can_impersonate'))

        # Call the middleware
        middleware = ImpersonationMiddleware()
        request = self.request_factory.get('/')
        request.session = {'impersonate_id': self.user.pk}
        request.user = self.admin
        middleware.process_request(request)
        self.assertEqual(request.user, self.user)

    def test_process_request_no_permission(self):
        """A user without permission should not be able to impersonate."""
        self.assertFalse(self.user.has_perm('accounts.can_impersonate'))
        middleware = ImpersonationMiddleware()
        request = self.request_factory.get('/')
        request.session = {'impersonate_id': self.admin.pk}
        request.user = self.user
        middleware.process_request(request)
        self.assertEqual(request.user, self.user)

    def test_process_request_superuser(self):
        """Superusers should be able to impersonate."""
        self.admin.is_superuser = True
        self.admin.save()
        self.assertTrue(self.admin.can_impersonate())

        # Call the middleware
        middleware = ImpersonationMiddleware()
        request = self.request_factory.get('/')
        request.session = {'impersonate_id': self.user.pk}
        request.user = self.admin
        middleware.process_request(request)
        self.assertEqual(request.user, self.user)

    def test_process_request_no_impersonate_id(self):
        """If impersonate_id isn't specified, user should stay the same."""
        # This user _could_ impersonate another user
        self.admin.is_superuser = True
        self.admin.save()
        self.assertTrue(self.admin.can_impersonate())

        middleware = ImpersonationMiddleware()
        request = self.request_factory.get('/')
        request.session = {}
        request.user = self.admin
        middleware.process_request(request)
        self.assertEqual(request.user, self.admin)

    def test_process_request_user_does_not_exist(self):
        """If impersonate_id doesn't correspond to a valid user, do nothing."""
        self.admin.is_superuser = True
        self.admin.save()
        self.assertTrue(self.admin.can_impersonate())

        # Call the middleware
        middleware = ImpersonationMiddleware()
        request = self.request_factory.get('/')
        request.session = {'impersonate_id': -1}
        request.user = self.admin
        middleware.process_request(request)
        self.assertEqual(request.user, self.admin)
