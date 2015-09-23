"""Validators for media app"""
from django.core.exceptions import ValidationError


def validate_unique_url(value):
    """Validate a shortened URL is unique"""
    from open_connect.media.models import ShortenedURL
    if ShortenedURL.objects.filter(url=value).exists():
        raise ValidationError(
            'URLs in shorterner must be unique', code='invalid')
