"""Tests for validators.py in media app"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from model_mommy import mommy

from open_connect.media import validators


class TestValidateUniqueURL(TestCase):
    """Tests for validate_unique_url"""
    def test_valid_url(self):
        """Test a valid URL that is not contained in the database"""
        # pylint: disable=no-self-use
        shortened = mommy.make(
            'media.ShortenedURL', url='http://short.bo/completely-unique')
        shortened.delete()

        # This will raise an exception if it is not unique and the test will
        # fail
        validators.validate_unique_url('http://short.bo/completely-unique')

    def test_invalid_url(self):
        """Test a url that already exists in the database"""
        mommy.make('media.ShortenedURL', url='http://short.bo/this-will-fail')
        with self.assertRaises(ValidationError) as context:
            validators.validate_unique_url('http://short.bo/this-will-fail')

        error = context.exception
        self.assertEqual(error.message, 'URLs in shorterner must be unique')
        self.assertEqual(error.code, 'invalid')
