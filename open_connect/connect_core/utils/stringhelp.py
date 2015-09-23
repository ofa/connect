"""String helper functions"""
from random import choice
from string import ascii_letters, digits


def str_or_empty(value):
    """Stringify an object, but if none return empty string"""
    if value is None:
        return ''
    else:
        return str(value)


def unicode_or_empty(value):
    """Unicode stringify an object, but if none return empty unicode string"""
    if value is None:
        return u''
    else:
        return unicode(value)


def str_to_bool(value):
    """Convert a string into a boolean"""
    if value.lower() in ("yes", "true", "t", "1"):
        return True
    if value.lower() in ("no", "false", "f", "0"):
        return False
    return None


def generate_random_string(length=10):
    """Generates a random string of any length."""
    return ''.join(choice(ascii_letters + digits) for _ in range(length))
