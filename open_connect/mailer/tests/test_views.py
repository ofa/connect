"""View tests for the mailer app"""
# pylint: disable=no-value-for-parameter,invalid-name

from django.http import Http404
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from model_mommy import mommy
from mock import Mock, patch

from open_connect.accounts.utils import generate_nologin_hash as hashgen
from open_connect.mailer import views
from open_connect.mailer.models import Unsubscribe
from open_connect.mailer.utils import url_representation_encode
from open_connect.mailer.tests.test_utils import (
    OPEN_DATA, OPEN_DATA_ENCODED, OPEN_DATA_HASH
)


@override_settings(EMAIL_SECRET_KEY='abcd')
class TestOpenView(TestCase):
    """Test the Process Tracking middleware"""
    def setUp(self):
        """Setup the Create Open Test"""
        self.view = views.OpenView.as_view()
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.META = Mock()

    def test_failed_hash_returns_404(self):
        """Test that a failing hash raises a Http404"""
        with self.assertRaises(Http404):
            self.view(self.request,
                      encoded_data=OPEN_DATA_ENCODED,
                      request_hash='aaaaaaaaaa')

    def test_missing_data_returns_404(self):
        """Test that not providing all required fields raises Http404"""
        data = {
            'e': 'me@razzmatazz.local'
        }
        representation, verification_hash = url_representation_encode(data)
        with self.assertRaises(Http404):
            self.view(self.request,
                      encoded_data=representation,
                      request_hash=verification_hash)

    @patch('open_connect.mailer.views.create_open')
    def test_process_request(self, mock):
        """Test a valid call to process_request"""
        result = self.view(
            self.request,
            encoded_data=OPEN_DATA_ENCODED,
            request_hash=OPEN_DATA_HASH)

        mock.assert_called_once_with(OPEN_DATA, self.request.META)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result['content-type'], 'image/gif')


class TestUnsubscribeView(TestCase):
    """Tests for the UnsubscribeView"""
    def setUp(self):
        """Setup the test"""
        self.view = views.UnsubscribeView.as_view()
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.email = 'test@test.com'
        self.code = hashgen(self.email)

    def test_valid_get_request(self):
        """Test a valid request returns a valid response"""
        self.request.GET = {
            'code': self.code,
            'email': self.email
        }
        result = self.view(self.request)
        self.assertEqual(result.status_code, 200)

    def test_dispatch_no_args(self):
        """
        Test that a 404 is returned by the dispatch method if no code is given
        """
        with self.assertRaises(Http404):
            self.request.GET = {}
            self.view(self.request)

    def test_dispatch_only_one_arg(self):
        """Test that a 404 is returned when only one arg is given"""
        with self.assertRaises(Http404):
            self.request.GET = {'email': self.email}
            self.view(self.request)

    def test_dispatch_non_valid_email(self):
        """Test that a 404 is returned with a non-valid email"""
        with self.assertRaises(Http404):
            self.request.GET = {
                'email': 'notanemail',
                'code': hashgen('notanemail')
            }
            self.view(self.request)

    def test_dispatch_non_valid_code(self):
        """Test that a 404 is thrown with a non-valid code"""
        with self.assertRaises(Http404):
            self.request.GET = {
                'email': self.email,
                'code': 'notavalidcode'
            }
            self.view(self.request)

    def test_context_contains_user(self):
        """Test that when a user exists the context has that user's account"""
        user = mommy.make('accounts.User', email='random_email@example.com')
        self.request.GET = {'email': user.email, 'code': user.private_hash}
        response = self.view(self.request)
        self.assertEqual(response.context_data['email'], user.email)
        self.assertEqual(response.context_data['account'], user)

    def test_context_contains_email(self):
        """Test that the context contains the email in the GET request"""
        self.request.GET = {'email': self.email, 'code': self.code}
        response = self.view(self.request)
        self.assertEqual(response.context_data['email'], self.email)

    def test_post_creates_record(self):
        """Test that a POST request generates a new Unsubscribe record"""
        self.assertFalse(Unsubscribe.objects.filter(
            address=self.email, source='user').exists())
        request = self.factory.post('/')
        request.GET = {'email': self.email, 'code': self.code}
        response = self.view(request)
        self.assertTrue(Unsubscribe.objects.filter(
            address=self.email, source='user').exists())
        self.assertEqual(response.status_code, 302)
