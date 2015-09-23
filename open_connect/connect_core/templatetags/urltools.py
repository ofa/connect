"""URL-based Templatetags"""
import os

from django import template
from django.conf import settings

# pylint: disable=invalid-name
register = template.Library()


@register.simple_tag
def clean_full_uri(request):
    """Return the full URI without querystrings"""
    return '%s://%s%s' % ('https' if request.is_secure() else 'http',
                          request.get_host(), request.path)

@register.simple_tag
def svgsprite(iconset):
    """Include sprite for an iconset"""
    path = os.path.join(settings.SVG_DIR, iconset, 'index.html')
    contents = open(path)
    return contents.read()
