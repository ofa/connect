"""Utility functions for the mailer app"""
from email.utils import getaddresses
import base64
import hashlib
import logging
import urllib
import urlparse
import re
import string
import uuid

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_text
from flanker.addresslib import address
from ua_parser import user_agent_parser

from open_connect.accounts.utils import generate_nologin_hash

ALLOWED_CHARS = (string.ascii_uppercase +
                 string.ascii_lowercase + string.digits)
ALLOWED_CHARS_PATTERN = '[^{alphabet}]'.format(alphabet=ALLOWED_CHARS)


LOGGER = logging.getLogger('mailer.utils')


def unsubscribe_url(email):
    """Unsubscribe URL to unsubscribe from all mailings"""
    origin = settings.ORIGIN
    unsub_url = reverse('unsubscribe')
    code = generate_nologin_hash(email.lower())
    return "{origin}{path}?email={email}&code={code}".format(
        origin=origin, path=unsub_url, email=email, code=code)


def url_representation_encode(data):
    """Turn a dictionary into an encoded base64 string and hash"""
    # Serialize the dictionary by urlencoding it
    url_encoded_string = urllib.urlencode(data)
    # Encode the serialized dictionary in base64 (provides some obscurity and
    # limits the number of special characters that can be in the URL
    base64_representation = base64.urlsafe_b64encode(
        url_encoded_string)
    # Remove the trailing padding character (equal sign)
    clean_base64_representation = base64_representation.strip('=')
    # Using a secret key from settings as a seed, generate a one-way hash of
    # the base64-encoded data. Only use the first 10 characters as our
    # needs do not require the security of a full hash.
    verification_hash = hashlib.md5(
        clean_base64_representation + settings.EMAIL_SECRET_KEY
        ).hexdigest()[:10]
    return clean_base64_representation, verification_hash


def url_representation_decode(base64_string):
    """Take an encoded string and convert it into a dictionary and hash"""
    # Generate a verification hash from the data passed in, using the a secret
    # key from settings as the hash
    verification_hash = hashlib.md5(
        base64_string + settings.EMAIL_SECRET_KEY).hexdigest()[:10]
    try:
        # Decode the string, adding the necessary amount of padding
        decoded = base64.urlsafe_b64decode(
            base64_string.encode('ascii') + '=' * (4 - len(base64_string) % 4))
    except TypeError:
        # If an improper string is passed in, catch the TypeError and return an
        # empty string
        decoded = ''
    return dict(urlparse.parse_qsl(decoded)), verification_hash


def clean_addresses(emails):
    """Takes a string of emails and returns a list of tuples of name/address
    pairs that are symanticly valid"""

    # Parse our string of emails, discarding invalid/illegal addresses
    valid_emails_list = address.parse_list(emails)

    # If no valid email addresses are found, return an empty list
    if not valid_emails_list:
        return []

    # If we have valid emails, use flanker's unicode address list creator to
    # give us something to pass to Python's email library's getaddresses
    valid_emails = valid_emails_list.to_unicode()

    # Return a list, in ('Name', 'email@dj.local')] form, the resulting emails
    email_list = getaddresses([valid_emails])

    # Lowercase all the email addresses in the list
    lowered_list = [(name, email.lower()) for name, email in email_list]
    return lowered_list


def generate_code():
    """Generate a unique 10 character code"""
    uuid_base64 = uuid.uuid4().hex.decode('hex').encode('base64')
    clean_uuid = re.sub(ALLOWED_CHARS_PATTERN, '', uuid_base64)
    return clean_uuid[0:10]


def prettify_agent_version(element):
    """Generate a processed string"""
    family = element['family']
    major = ' %s' % element['major'] if element.get('major') else ''
    minor = '.%s' % element['minor'] if element.get('minor') else ''
    patch = '.%s' % element['patch'] if element.get('patch') else ''
    return '{family}{version}{minor}{patch}'.format(
        family=family, version=major, minor=minor, patch=patch)


def process_useragent(useragent):
    """Convert a useragent into something useful"""
    parsed_agent = user_agent_parser.Parse(useragent)

    browser = prettify_agent_version(parsed_agent['user_agent'])
    operating_system = prettify_agent_version(parsed_agent['os'])
    device = parsed_agent['device']['family']
    return (operating_system, browser, device)


def create_open(data, headers):
    """Create and save the new EmailOpen object"""
    # We must import EmailOpen here to avoid nasty import problems
    from open_connect.mailer.models import EmailOpen
    open_object = EmailOpen()
    open_object.email = data['e']
    open_object.timestamp = parse_datetime(data['t'])
    open_object.key = data['k']

    # If there is a notification ID, it needs to be an integer
    if 'n' in data:
        open_object.notification = int(data['n'])

    ip_addresses = headers.get(
        'HTTP_X_FORWARDED_FOR', headers.get('REMOTE_ADDR')).split(',')
    if ip_addresses:
        open_object.ip_address = ip_addresses[0]

    user_agent = headers.get('HTTP_USER_AGENT', '')
    open_object.user_agent = user_agent[0:1000]
    raw_referrer = headers.get('HTTP_REFERER', None)
    if raw_referrer:
        referrer = force_text(raw_referrer, errors='replace')
        parsed_referrer = urlparse.urlparse(referrer)
        open_object.referrer_netloc = parsed_referrer.netloc[0:1000]
        open_object.referrer = referrer[0:1000]

    if user_agent:
        operating_system, browser, device = process_useragent(user_agent)
        open_object.operating_system = operating_system
        open_object.browser = browser
        open_object.device_family = device

    # Create the object
    open_object.save()


def send_email(email, from_email, subject, text, html):
    """Quick 'send email' shortcut"""
    message = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=from_email,
        to=(email,)
    )
    message.attach_alternative(
        content=html,
        mimetype='text/html'
    )
    message.send()
    LOGGER.info(u"Email: %s Subject: %s", email, subject)
