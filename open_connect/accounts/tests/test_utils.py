"""Tests of the utils file in the accounts app"""
from django.test import TestCase

from open_connect.accounts import utils


class TestAccountUtils(TestCase):
    """Test utility functions in the accounts app"""
    def test_hash_gen(self):
        """Test the hash gen"""
        response = utils.generate_nologin_hash('teststring')

        # Assert that we got a string that contains something
        self.assertEqual(type(response), str)
        self.assertTrue(response)

        # A SHA256 hash is 64 characters long. Since we convert
        # it to base64, it should always be lower
        self.assertTrue(len(response) < 64)

        # The raw base64 representation includes a trailing equals sign
        # ensure that was removed
        self.assertNotIn('=', response)
