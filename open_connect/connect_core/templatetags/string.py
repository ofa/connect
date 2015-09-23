"""String-related Templatetags"""
from django import template

# pylint: disable=invalid-name
register = template.Library()


@register.filter("padded_slice", is_safe=True)
def padded_slice_filter(value, page_number):
    """
    Templatetag which takes a value and returns a padded slice
    """
    try:
        bits = []
        padding = 5
        page_number = int(page_number)

        if page_number - padding < 1:
            bits.append(None)
        else:
            bits.append(page_number - padding)

        if page_number + padding > len(value):
            bits.append(len(value))
        else:
            bits.append(page_number + padding)

        return value[slice(*bits)]
    except (ValueError, TypeError):
        # Fail silently.
        return value


@register.filter('input_type')
def input_type(form_field):
    """
    Filter which returns the name of the formfield widget
    """
    return form_field.field.widget.__class__.__name__
