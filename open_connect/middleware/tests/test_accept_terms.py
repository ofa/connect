"""Tests for accepting terms middleware."""
# pylint: disable=invalid-name
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory
from django.utils.timezone import now
from model_mommy import mommy

from open_connect.middleware.accept_terms import AcceptTermsAndConductMiddleware


class TestAcceptTermsAndConductMiddleware(TestCase):
    """Tests for AcceptTermsAndConductMiddleware."""
    def setUp(self):
        """Setup the TestAcceptTermsAndConductMiddleware TestCase"""
        self.factory = RequestFactory()
        self.mw = AcceptTermsAndConductMiddleware()

    def test_user_is_not_authenticated(self):
        """If user is not authenticated, ignore."""
        request = self.factory.get('/')
        request.user = AnonymousUser()
        self.assertIsNone(self.mw.process_request(request))

    def test_user_has_accepted_terms_and_conduct(self):
        """If user has accepted terms and conduct, carry on."""
        user = mommy.make(
            'accounts.User', tos_accepted_at=now(), ucoc_accepted_at=now())
        request = self.factory.get('/')
        request.user = user
        self.assertIsNone(self.mw.process_request(request))

    def test_url_is_exempt(self):
        """If url is exempt from checking, carry on."""
        user = mommy.make(
            'accounts.User', tos_accepted_at=None, ucoc_accepted_at=None)
        request = self.factory.get('/accounts/login/')
        request.user = user
        self.assertIsNone(self.mw.process_request(request))

    def test_user_has_not_accepted_terms(self):
        """If user has not accepted terms, force them to."""
        user = mommy.make(
            'accounts.User', tos_accepted_at=None, ucoc_accepted_at=now())
        request = self.factory.get('/inbox/')
        request.user = user
        self.assertEqual(
            self.mw.process_request(request)['Location'],
            '{url}?next=/inbox/'.format(url=reverse('accept_terms_and_conduct'))
        )

    def test_user_has_not_accepted_ucoc(self):
        """If user has not accepted code of conduct, force them to."""
        user = mommy.make(
            'accounts.User', tos_accepted_at=now(), ucoc_accepted_at=None)
        request = self.factory.get('/inbox/')
        request.user = user
        self.assertEqual(
            self.mw.process_request(request)['Location'],
            '{url}?next=/inbox/'.format(url=reverse('accept_terms_and_conduct'))
        )
