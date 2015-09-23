"""Test the utils file for the mailer app"""
# pylint: disable=invalid-name
import base64

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.dateparse import parse_datetime

from mock import Mock, patch
from open_connect.accounts.utils import generate_nologin_hash
from open_connect.mailer import utils
from open_connect.mailer.models import EmailOpen


# The proper url_represenatation_encode version of OPEN_DATA
OPEN_DATA_ENCODED = ('az11TFNiZ0FTd1drJmU9bWUlNDByYXp6bWF0YXp6LmxvY2FsJnQ9MjAx'
                     'NC0wNC0wNysxNyUzQTAxJTNBMTIlMkIwMCUzQTAwJm49MTA')

# The url_represenatation_encode hash that assumes EMAIL_SECRET_KEY is 'abcd'
OPEN_DATA_HASH = 'e3ace8b556'
OPEN_DATA = {
    'e': 'me@razzmatazz.local',
    'k': 'uLSbgASwWk',
    'n': '10',
    't': '2014-04-07 17:01:12+00:00'
}
DEMO_USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2)'
                   ' AppleWebKit/537.36 (KHTML, like Gecko)'
                   ' Chrome/33.0.1750.152 Safari/537.36')


@override_settings(ORIGIN='http://connect.local', EMAIL_SECRET_KEY='abcd')
class TestUnsubscribeURLGenerator(TestCase):
    """Test the unsubscribe_url function"""
    def test_unsubscribe_url(self):
        """Test that all the required components are in the URL"""
        result = utils.unsubscribe_url('test123@example.com')
        unsub_url = reverse('unsubscribe')
        code = generate_nologin_hash('test123@example.com')

        self.assertIn(unsub_url, result)
        self.assertIn('code=%s' % code, result)
        self.assertIn('email=test123@example.com', result)
        self.assertIn('http://connect.local', result)


@override_settings(EMAIL_SECRET_KEY='abcd')
class TestUrlRepresentationProcessing(TestCase):
    """Tests for url_representation_encode and url_representation_decode"""

    def test_url_representation_encode(self):
        """Test the url_representation_encode functionality"""
        # As we're passing in a dictionary we cannot guarantee that the order
        # of the URL string will be consistent, so we'll have to test for both
        encoded_options = [
            base64.urlsafe_b64encode('first=Stanley&last=Smith').strip('='),
            base64.urlsafe_b64encode('last=Smith&first=Stanley').strip('=')
        ]

        data = {
            'first': 'Stanley',
            'last': 'Smith'
        }

        code, verification_hash = utils.url_representation_encode(data)

        self.assertTrue(any([option == code for option in encoded_options]))

        # Ensure that the verification hash is a 10 character string
        self.assertEqual(len(verification_hash), 10)
        self.assertIsInstance(verification_hash, str)

    def test_url_representation_decode(self):
        """Test the url_representation_decode functionality"""
        result, verification_hash = utils.url_representation_decode(
            OPEN_DATA_ENCODED)

        self.assertDictEqual(result, OPEN_DATA)
        self.assertEqual(verification_hash, OPEN_DATA_HASH)

    def test_roundtrip(self):
        """Test that an identical dictionary can be encoded and decoded"""
        test_dict = {
            'special_char': '%##!@#9813&&&&',
            'email': 'me@razzmatazz.local'
        }
        code, verification_hash = utils.url_representation_encode(test_dict)

        # Decode the data, verify we can reverse the process
        decoded_data, decoded_hash = utils.url_representation_decode(code)
        self.assertEqual(decoded_hash, verification_hash)
        self.assertDictEqual(decoded_data, test_dict)


class TestAddressCleaner(TestCase):
    """Test the address_cleaner function"""
    def test_valid_list(self):
        """Test where every address is valid"""
        emails = ('Nick Cat <nickcat@dj.local>, Jordan <jordan@dj.local>,'
                  'Jack <jotus@dj.local>, Grace <gotus@dj.local>')
        result = utils.clean_addresses(emails)
        self.assertEqual(result, [
            ('Nick Cat', 'nickcat@dj.local'), ('Jordan', 'jordan@dj.local'),
            ('Jack', 'jotus@dj.local'), ('Grace', 'gotus@dj.local')
        ])

    def test_with_invalid_addresses(self):
        """Test where there are some invalid email addresses"""
        emails = ('Nick Cat <nickcat@dj.local>, Jordan <jordan@dj.local>,'
                  'Jack <jotus@dj.local>, tester@, Not An Email,'
                  'Bad Address <@>, Grace <gotus@dj.local>')
        result = utils.clean_addresses(emails)
        self.assertEqual(result, [
            ('Nick Cat', 'nickcat@dj.local'), ('Jordan', 'jordan@dj.local'),
            ('Jack', 'jotus@dj.local'), ('Grace', 'gotus@dj.local')
        ])

    def test_empty_list(self):
        """Test where an empty string is passed to the function"""
        result = utils.clean_addresses('')
        self.assertEqual(result, [])

    def test_lowercase_email_addresses(self):
        """Test that the function lowercases all addresses"""
        emails = ('Nick Cat <niCkcAt@dj.local>, Jordan <Jordan@dj.local>,'
                  'Jack <JotUS@dj.local>, Grace <GotUS@dj.local>')
        result = utils.clean_addresses(emails)
        self.assertEqual(result, [
            ('Nick Cat', u'nickcat@dj.local'), ('Jordan', 'jordan@dj.local'),
            ('Jack', 'jotus@dj.local'), ('Grace', 'gotus@dj.local')
        ])


@override_settings(EMAIL_SECRET_KEY='abcd')
class TestGenerateCode(TestCase):
    """Tests for generate_code"""
    def test_generate_code(self):
        """Test the generate_code function returns a 10 character string"""
        code = utils.generate_code()
        self.assertEqual(len(code), 10)
        self.assertIsInstance(code, str)

    @patch('open_connect.mailer.utils.uuid')
    def test_generate_code_removes_special_characters(self, mock):
        """Test the generate code special character removal functionality."""
        mock.uuid4().hex.decode().encode.return_value = '1+2#3*4/5+6-7%8+90ABC'
        code = utils.generate_code()
        # Ensure that the result is the base64 code
        self.assertEqual(code, '1234567890')


class TestUserAgentProcessing(TestCase):
    """Tests for User Agent Processing Functionality"""
    def test_prettify_agent_no_minor_no_patch(self):
        """Test the prettify_agent_version with no minor or patch number"""
        data = {
            'family': 'Internet Explorer',
            'major': '10'
        }
        result = utils.prettify_agent_version(data)
        self.assertEqual(result, 'Internet Explorer 10')

    def test_prettify_agent(self):
        """Test the prettify_agent_version with all fields"""
        data = {
            'family': 'Chrome',
            'major': '33',
            'minor': '0',
            'patch': '1750'
        }
        result = utils.prettify_agent_version(data)
        self.assertEqual(result, 'Chrome 33.0.1750')

    def test_processuseragent_desktop(self):
        """Test the process useragent function with a desktop client"""
        operating_system, browser, device = utils.process_useragent(
            DEMO_USER_AGENT)
        self.assertEqual(operating_system, 'Mac OS X 10.9.2')
        self.assertEqual(browser, 'Chrome 33.0.1750')
        self.assertEqual(device, 'Other')

    def test_process_user_agent_mobile(self):
        """Test the process useragent function with a mobile client"""
        user_agent = ('Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X)'
                      ' AppleWebKit/536.26 (KHTML, like Gecko)'
                      ' Version/6.0 Mobile/10A5376e Safari/8536.25')
        operating_system, browser, device = utils.process_useragent(user_agent)
        self.assertEqual(operating_system, 'iOS 6.0')
        self.assertEqual(browser, 'Mobile Safari 6.0')
        self.assertEqual(device, 'iPhone')


class TestCreateOpen(TestCase):
    """Test the create_open function"""
    def setUp(self):
        """Setup the Create Open Test"""
        self.headers = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': DEMO_USER_AGENT,
            'HTTP_REFERER': 'https://mail.google.com/mail/u/1/'
        }

    def test_open(self):
        """Test a full open creation"""
        initial_count = EmailOpen.objects.count()
        utils.create_open(OPEN_DATA, self.headers)
        new_count = EmailOpen.objects.count()

        self.assertEqual(new_count, initial_count + 1)

        new_open = EmailOpen.objects.latest('pk')
        self.assertEqual(new_open.email, 'me@razzmatazz.local')
        self.assertEqual(
            new_open.timestamp,
            parse_datetime('2014-04-07 17:01:12+00:00')
        )
        self.assertEqual(new_open.notification, 10)
        self.assertEqual(new_open.ip_address, '127.0.0.1')
        self.assertEqual(
            new_open.user_agent,
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2)'
            ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152'
            ' Safari/537.36'
        )
        self.assertEqual(new_open.referrer_netloc, 'mail.google.com')
        self.assertEqual(
            new_open.referrer, 'https://mail.google.com/mail/u/1/')
        self.assertEqual(new_open.operating_system, 'Mac OS X 10.9.2')
        self.assertEqual(new_open.browser, 'Chrome 33.0.1750')
        self.assertEqual(new_open.device_family, 'Other')

    def test_open_no_notification(self):
        """Test creating an open without a notification id"""
        initial_count = EmailOpen.objects.count()
        data = OPEN_DATA.copy()
        del data['n']
        utils.create_open(data, self.headers)
        new_count = EmailOpen.objects.count()

        self.assertEqual(new_count, initial_count + 1)

        new_open = EmailOpen.objects.latest('pk')
        self.assertIsNone(new_open.notification)

    def test_open_no_referrer(self):
        """Test creating an open without a referrer"""
        initial_count = EmailOpen.objects.count()
        headers = self.headers.copy()
        del headers['HTTP_REFERER']
        utils.create_open(OPEN_DATA, headers)
        new_count = EmailOpen.objects.count()

        self.assertEqual(new_count, initial_count + 1)

        new_open = EmailOpen.objects.latest('pk')
        self.assertIsNone(new_open.referrer_netloc)
        self.assertIsNone(new_open.referrer)

    def test_open_no_user_agent(self):
        """Test creating an open without a user agent"""
        initial_count = EmailOpen.objects.count()
        headers = self.headers.copy()
        del headers['HTTP_USER_AGENT']
        utils.create_open(OPEN_DATA, headers)
        new_count = EmailOpen.objects.count()

        self.assertEqual(new_count, initial_count + 1)

        new_open = EmailOpen.objects.latest('pk')
        self.assertIsNone(new_open.operating_system)
        self.assertIsNone(new_open.browser)
        self.assertIsNone(new_open.device_family)

    def test_multiple_ip_addresses(self):
        """X_FORWARDED_FOR can sometimes send multiple IPs, should use first."""
        initial_count = EmailOpen.objects.count()
        headers = self.headers.copy()
        headers['HTTP_X_FORWARDED_FOR'] = '1.1.1.1, 2.2.2.2, 3.3.3.3'
        utils.create_open(OPEN_DATA, headers)
        new_count = EmailOpen.objects.count()

        self.assertEqual(new_count, initial_count + 1)

        new_open = EmailOpen.objects.latest('pk')
        self.assertEqual(new_open.ip_address, '1.1.1.1')


@patch.object(utils, 'EmailMultiAlternatives')
class TestSendEmail(TestCase):
    """Test the send_email helper"""
    # pylint: disable=no-self-use
    def test_send_email(self, mock):
        """Test the functionality of the send_email helper"""
        email_mock = Mock()
        mock.return_value = email_mock

        utils.send_email(
            email='gracegrant@razzmatazz.local',
            from_email='no-reply@razzmatazz.local',
            subject='Updates',
            text='You have a new message. someurl',
            html='this is my snippet someurl'
        )

        mock.assert_called_once_with(
            body='You have a new message. someurl',
            to=(u'gracegrant@razzmatazz.local',),
            subject='Updates',
            from_email='no-reply@razzmatazz.local'
        )
        email_mock.attach_alternative.assert_called_once_with(
            mimetype='text/html', content='this is my snippet someurl'
        )
