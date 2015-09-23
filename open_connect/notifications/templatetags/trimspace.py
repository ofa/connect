"""Space trim templatetag"""
# pylint: disable=invalid-name

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def trim(value):
    """Space trim templatetag"""
    return value.replace(" ", "-")
