"""Mailing templatetags"""
from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from open_connect.mailer.utils import (
    unsubscribe_url, url_representation_encode, generate_code
)

# pylint: disable=invalid-name
register = template.Library()

@register.simple_tag
def unsubscribe_link(email):
    """Tag which returns the URL to unsubscribe for an email"""
    return unsubscribe_url(email)


@register.simple_tag
def origin():
    """Tag which returns the protocol and hostname"""
    return settings.ORIGIN


@register.simple_tag
def brand_title():
    """Tag which returns the local title of Connect"""
    return settings.BRAND_TITLE


@register.simple_tag
def organization():
    """Tag which returns the organization sponsoring connect"""
    return settings.ORGANIZATION


@register.simple_tag
def email_image_max_width(image, max_width, extras=''):
    """Return an <img> tag with max_width filled in"""
    aspect_ratio = float(image.image_width) / float(image.image_height)
    new_height = int(max_width / aspect_ratio)

    components = {
        'url': "{origin}{path}".format(
            origin=settings.ORIGIN,
            path=reverse(
                'custom_image_version',
                kwargs={
                    'image_uuid': image.uuid,
                    'image_type': 'display_image'
                })),
        'height': new_height,
        'width': max_width,
        'extras': extras
    }
    return mark_safe(('<img src="{url}" width="{width}" height="{height}"'
                      ' border="0" {extras} />').format(**components))


@register.simple_tag
def tracking_pixel(email, notification_id=None):
    """Returns a mailing tracking pixel"""
    data = {
        # Email Address
        'e': email,
        # Unique Key
        'k': generate_code(),
        # Current Time (Without microseconds, in ISOFormat)
        't': now().replace(microsecond=0).isoformat(),
    }
    # Add Notification ID (if available)
    if notification_id:
        data['n'] = notification_id

    encoded_data, verification_hash = url_representation_encode(data)
    gif_url = reverse(
        'email_open',
        kwargs={
            'encoded_data': encoded_data,
            'request_hash': verification_hash
        }
    )
    # Add our local tracking pixel
    local_tracking = ('<img src="{origin}{location}" width="1" height="1"'
                      ' border="0">').format(origin=settings.ORIGIN,
                                             location=gif_url)
    return local_tracking
