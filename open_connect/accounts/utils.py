"""Utility functions for accounts"""
import string
from hashlib import sha256
from re import sub

from django.conf import settings

ESCAPED_URL_ALPHABET = (string.ascii_uppercase +
                        string.ascii_lowercase +
                        string.digits + r'\-\_')


def generate_nologin_hash(public_string):
    """Generate hash for users who are not logged in"""
    hex_hash = sha256(settings.EMAIL_SECRET_KEY + public_string).hexdigest()

    # Decode the hex hash into base64, reducing the length of the code
    b64_hash = hex_hash.decode('hex').encode("base64")

    # Remove all characters not in our accepted URL-safe alphabet
    regex_pattern = '[^{alphabet}]'.format(alphabet=ESCAPED_URL_ALPHABET)
    return sub(regex_pattern, '', b64_hash)
