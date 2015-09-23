"""Tests for visit tracking middleware."""
# pylint: disable=invalid-name
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory

from django.test.utils import override_settings
from mock import Mock
from model_mommy import mommy

from open_connect.middleware.visit_tracking import VisitTrackingMiddleware
from open_connect.accounts.models import Visit
from open_connect.connect_core.utils.basetests import ConnectTestMixin


User = get_user_model()


middleware = list(settings.MIDDLEWARE_CLASSES)
# pylint: disable=line-too-long
if 'open_connect.middleware.visit_tracking.VisitTrackingMiddleware' not in middleware:
    middleware.insert(
        0, 'open_connect.middleware.visit_tracking.VisitTrackingMiddleware')


@override_settings(MIDDLEWARE_CLASSES=middleware)
class VisitTrackingMiddlewareTest(ConnectTestMixin, TestCase):
    """Tests for visit tracking middleware."""
    def test_no_user_attribute(self):
        """Test that a request without a user attr won't trigger an error"""
        user = mommy.make(User)
        request_factory = RequestFactory()
        visit_tracking_mw = VisitTrackingMiddleware()

        visit_count = Visit.objects.count()
        request1 = request_factory.get('/')
        response1 = Mock()
        self.assertFalse(hasattr(request1, 'user'))
        result1 = visit_tracking_mw.process_response(request1, response1)
        self.assertEqual(response1, result1)
        self.assertEqual(visit_count, Visit.objects.count())

        request2 = request_factory.get('/')
        response2 = Mock()
        request2.user = user
        self.assertTrue(hasattr(request2, 'user'))
        visit_tracking_mw.process_response(request2, response2)
        self.assertEqual(Visit.objects.count(), visit_count + 1)

    def test_unauthenticated_requests_not_logged(self):
        """Anonymous users shouldn't have their visits logged."""
        visit_count = Visit.objects.count()
        self.client.get('/')
        self.assertIsNone(self.client.cookies.get('visit_logged'))
        self.assertEqual(Visit.objects.count(), visit_count)

    def test_authenticated_requests_logged(self):
        """An authenticated user should have their visit logged."""
        visit_count = Visit.objects.count()
        User.objects.create_user(username='a@b.local', password='moo')
        self.client.post(
            reverse('login'), {'username': 'a@b.local', 'password': 'moo'})
        self.client.get('/')
        self.assertEqual(self.client.cookies.get('visit_logged').value, '1')
        self.assertEqual(Visit.objects.count(), visit_count + 1)

    def test_authenticated_requests_not_logged_twice_in_same_period(self):
        """An authenticated users hould only have their visit logged 1x/day."""
        visit_count = Visit.objects.count()
        User.objects.create_user(username='a@b.local', password='moo')
        self.client.post(
            reverse('login'), {'username': 'a@b.local', 'password': 'moo'})
        self.client.get('/')
        self.assertEqual(Visit.objects.count(), visit_count + 1)
        self.client.get('/')
        self.assertEqual(Visit.objects.count(), visit_count + 1)
