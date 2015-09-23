# -*- coding: utf-8 -*-
# Disable all pylint errors for 3rd party code
# pylint: disable=all
"""Backport of django.utils.html.clean_html

django.utils.html.clean_html was removed in Django 1.8 but Connect still relies
on it.
"""
import re

from django.utils.encoding import force_text
from django.utils.text import normalize_newlines

# List of possible strings used for bullets in bulleted lists.
DOTS = ['&middot;', '*', '\u2022', '&#149;', '&bull;', '&#8226;']

# pylint: disable=line-too-long
link_target_attribute_re = re.compile(r'(<a [^>]*?)target=[^\s>]+')
html_gunk_re = re.compile(r'(?:<br clear="all">|<i><\/i>|<b><\/b>|<em><\/em>|<strong><\/strong>|<\/?smallcaps>|<\/?uppercase>)', re.IGNORECASE)
hard_coded_bullets_re = re.compile(r'((?:<p>(?:%s).*?[a-zA-Z].*?</p>\s*)+)' % '|'.join([re.escape(x) for x in DOTS]), re.DOTALL)
trailing_empty_content_re = re.compile(r'(?:<p>(?:&nbsp;|\s|<br \/>)*?</p>\s*)+\Z')
unencoded_ampersands_re = re.compile(r'&(?!(\w+|#\d+);)')


def fix_ampersands(value):
    """Returns the given HTML with all unencoded ampersands encoded correctly."""
    return unencoded_ampersands_re.sub('&amp;', force_text(value))


def clean_html(text):
    """
    Clean the given HTML.  Specifically, do the following:
        * Convert <b> and <i> to <strong> and <em>.
        * Encode all ampersands correctly.
        * Remove all "target" attributes from <a> tags.
        * Remove extraneous HTML, such as presentational tags that open and
          immediately close and <br clear="all">.
        * Convert hard-coded bullets into HTML unordered lists.
        * Remove stuff like "<p>&nbsp;&nbsp;</p>", but only if it's at the
          bottom of the text.
    """
    text = normalize_newlines(force_text(text))
    text = re.sub(r'<(/?)\s*b\s*>', '<\\1strong>', text)
    text = re.sub(r'<(/?)\s*i\s*>', '<\\1em>', text)
    text = fix_ampersands(text)
    # Remove all target="" attributes from <a> tags.
    text = link_target_attribute_re.sub('\\1', text)
    # Trim stupid HTML such as <br clear="all">.
    text = html_gunk_re.sub('', text)
    # Convert hard-coded bullets into HTML unordered lists.

    def replace_p_tags(match):
        s = match.group().replace('</p>', '</li>')
        for d in DOTS:
            s = s.replace('<p>%s' % d, '<li>')
        return '<ul>\n%s\n</ul>' % s
    text = hard_coded_bullets_re.sub(replace_p_tags, text)
    # Remove stuff like "<p>&nbsp;&nbsp;</p>", but only if it's at the bottom
    # of the text.
    text = trailing_empty_content_re.sub('', text)
    return text
