# -*- coding: utf-8 -*-
# Disable all pylint errors for 3rd party code
# pylint: disable=all
"""Tests for the clean_html backport

This is a near clone of the relevant tests found in Django 1.6's
django.tests.utils_test.test_html
"""
from __future__ import unicode_literals

from django.utils.unittest import TestCase

# pylint: disable=line-too-long
from open_connect.connect_core.utils.third_party.django_clean_html_backport import (
    clean_html, fix_ampersands
)


class TestCleanHtmlBackport(TestCase):
    """Test the backported HTML functionality"""
    def check_output(self, function, value, output=None):
        """
        Check that function(value) equals output.  If output is None,
        check that function(value) equals value.
        """
        if output is None:
            output = value
        self.assertEqual(function(value), output)

    def test_fix_ampersands(self):
        """Test the fix_ampersands function"""
        # Strings without ampersands or with ampersands already encoded.
        values = ("a&#1;", "b", "&a;", "&amp; &x; ", "asdf")
        patterns = (
            ("%s", "%s"),
            ("&%s", "&amp;%s"),
            ("&%s&", "&amp;%s&amp;"),
        )
        for value in values:
            for in_pattern, out_pattern in patterns:
                self.check_output(
                    fix_ampersands, in_pattern % value, out_pattern % value)
        # Strings with ampersands that need encoding.
        items = (
            ("&#;", "&amp;#;"),
            ("&#875 ;", "&amp;#875 ;"),
            ("&#4abc;", "&amp;#4abc;"),
        )
        for value, output in items:
            self.check_output(fix_ampersands, value, output)

    def test_clean_html(self):
        """Test the clean_html function"""
        items = (
            ('<p>I <i>believe</i> in <b>semantic markup</b>!</p>', '<p>I <em>believe</em> in <strong>semantic markup</strong>!</p>'),
            ('I escape & I don\'t <a href="#" target="_blank">target</a>', 'I escape &amp; I don\'t <a href="#" >target</a>'),
            ('<p>I kill whitespace</p><br clear="all"><p>&nbsp;</p>', '<p>I kill whitespace</p>'),
            # also a regression test for #7267: this used to raise an UnicodeDecodeError
            ('<p>* foo</p><p>* bar</p>', '<ul>\n<li> foo</li><li> bar</li>\n</ul>'),
        )
        for value, output in items:
            self.check_output(clean_html, value, output)
