"""Test handle_ip.py middleware"""
# pylint: disable=invalid-name
from django.test import TestCase
from mock import Mock

from open_connect.middleware.handle_ip import SetCorrectIPMiddleware


class TestSetCorrectIPMiddleware(TestCase):
    """Tests for SetCorrectIPMiddleware"""
    def setUp(self):
        """Setup the test"""
        self.middleware = SetCorrectIPMiddleware()

    def test_multiple_ip(self):
        """Test that the correct IP is returned with multiple IPs"""
        mock_request = Mock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': u"8.8.8.8, 10.228.26.24",
            'REMOTE_ADDR': u"10.228.26.24"
        }
        self.middleware.process_request(mock_request)
        self.assertEqual(mock_request.META["REMOTE_ADDR"], u"8.8.8.8")
        self.assertEqual(mock_request.META["HTTP_X_FORWARDED_FOR"], u"8.8.8.8")

    def test_single_ip(self):
        """Test that the correct IP is returned with a single remote IP"""
        mock_request = Mock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': u"8.8.8.8",
            'REMOTE_ADDR': u"10.228.26.24"
        }
        self.middleware.process_request(mock_request)
        self.assertEqual(mock_request.META["REMOTE_ADDR"], u"8.8.8.8")
        self.assertEqual(mock_request.META["HTTP_X_FORWARDED_FOR"], u"8.8.8.8")

    def test_sets_both(self):
        """Test that both REMOTE_ADDR and HTTP_X_FORWARDED_FOR are always set"""
        mock_request = Mock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': u"8.8.8.8",
        }
        self.middleware.process_request(mock_request)
        self.assertEqual(mock_request.META["REMOTE_ADDR"], u"8.8.8.8")
        self.assertEqual(mock_request.META["HTTP_X_FORWARDED_FOR"], u"8.8.8.8")

    def test_no_meta_header(self):
        """Test if there is no IP meta available (mostly in a test)"""
        mock_request = Mock()
        mock_request.META = {
            'X-Nothing-Here': 'Nothing'
        }
        self.middleware.process_request(mock_request)
        self.assertNotIn("REMOTE_ADDR", mock_request.META)
