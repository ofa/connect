"""Tests for the Google Analytics context processor"""
from django.test import TestCase
from django.test.utils import override_settings

from open_connect.context_processors.google_analytics import google_analytics


class TestGoogleAnalytics(TestCase):
    """Test the google_analytics Context Processor"""
    @override_settings(GA_PROPERTYID='UA-99999-1')
    def test_ga_id(self):
        """Test that a ga_id is properly returned"""
        result = google_analytics(None)
        self.assertEqual(result['ga']['id'], 'UA-99999-1')

    @override_settings(GA_DEBUG_MODE=True)
    def test_ga_debug(self):
        """Test that ga_debug is trust"""
        result = google_analytics(None)
        self.assertEqual(result['ga']['debug'], True)

    @override_settings(GA_DEBUG_MODE=False)
    def test_ga_debug_false(self):
        """Test that ga_debug is false"""
        result = google_analytics(None)
        self.assertEqual(result['ga']['debug'], False)
