"""Test stringhelp.py utilities"""
from django.test import TestCase

from open_connect.connect_core.utils.stringhelp import (
    str_or_empty, unicode_or_empty, str_to_bool
)


class TestStringUtils(TestCase):
    """Testcase for string utilities"""
    def test_str_or_empty(self):
        """Test str_or_empty() function"""
        self.assertEqual(str_or_empty(None), '')
        self.assertEqual(str_or_empty(True), 'True')
        self.assertIsInstance(str_or_empty(None), str)

    def test_unicode_or_empty(self):
        """Test unicode_or_empty() function"""
        self.assertEqual(unicode_or_empty(None), u'')
        self.assertEqual(unicode_or_empty(True), u'True')
        self.assertIsInstance(unicode_or_empty(None), unicode)

    def test_str_to_bool(self):
        """Test str_to_bool() function"""
        self.assertTrue(str_to_bool("yes"))
        self.assertTrue(str_to_bool("true"))
        self.assertTrue(str_to_bool("TRUE"))
        self.assertTrue(str_to_bool("T"))
        self.assertTrue(str_to_bool("1"))

        self.assertFalse(str_to_bool("NO"))
        self.assertFalse(str_to_bool("false"))
        self.assertFalse(str_to_bool("0"))

        self.assertIsNone(str_to_bool("maybe"))
