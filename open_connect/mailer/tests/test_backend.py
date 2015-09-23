"""Mail backend tests for mailer app"""
from django.test import TestCase
from django.test.utils import override_settings
from django.core import mail
from model_mommy import mommy


def message_maker(email_to, **kwargs):
    """Email message builder"""
    return mail.EmailMessage(
        'Demo Message Subject',
        'Demo Body',
        'demo@razzmatazz.local',
        email_to,
        **kwargs
    )


@override_settings(
    ORIGINAL_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class TestConnectMailerBackend(TestCase):
    """Test the ConnectMailerBackend email backend"""
    def setUp(self):
        """Setup the mailer backend test"""
        # Because we determine the mailer backend based a setting, we must
        # import the mailer backend after we've already overridden the settings
        from open_connect.mailer.backend import ConnectMailerBackend
        self.backend = ConnectMailerBackend

        # We need 2 demo email addresses. One of them should be unsubscribed.
        self.valid_address = 'valid-address@example.local'
        self.banned_address = 'unsubscribed-address@example.local'
        mommy.make('mailer.Unsubscribe', address=self.banned_address)

    def test_valid_message_sent(self):
        """Test that a fully valid, non-unsubscribed email is sent"""
        # When using the `locmem` email backend, the attribute
        # `django.core.mail.outbox` is created and filled with sent messages.
        # We can check reset the outbox on each test then look for messages we
        # expect are in the outbox and make sure the ones we don't want aren't
        # in the outbox.
        mail.outbox = []

        valid_message = message_maker([self.valid_address])
        result = self.backend().send_messages([valid_message])

        self.assertEqual(result, 1)
        self.assertEqual(mail.outbox, [valid_message])

    def test_invalid_message_not_sent(self):
        """Test that sending a single invalid email results in no call"""
        mail.outbox = []

        banned_message = message_maker([self.banned_address])
        result = self.backend().send_messages([banned_message])

        self.assertEqual(result, 0)
        self.assertEqual(mail.outbox, [])

    def test_one_send_invalid_message_valid_message(self):
        """Test that when an invalid message and a valid message are passed
        only the invalid message is sent"""
        mail.outbox = []

        valid_message = message_maker([self.valid_address])
        invalid_message = message_maker([self.banned_address])

        result = self.backend().send_messages(
            [valid_message, invalid_message])

        self.assertEqual(result, 1)
        self.assertEqual(mail.outbox[0].to, [self.valid_address])
        self.assertEqual(mail.outbox, [valid_message])

    def test_one_valid_one_invalid_address_same_message(self):
        """Test that an email to both a valid and invalid address is only
        sent to the valid address"""
        mail.outbox = []

        message = message_maker([self.valid_address, self.banned_address])

        result = self.backend().send_messages([message])

        self.assertEqual(result, 1)
        self.assertEqual(mail.outbox[0].to, [self.valid_address])

    def test_invalid_to_valid_cc(self):
        """
        Test that when the invalid address is the only 'to' the message is not
        sent
        """
        mail.outbox = []

        message = message_maker([self.banned_address], cc=[self.valid_address])

        result = self.backend().send_messages([message])

        self.assertEqual(result, 0)
        self.assertEqual(mail.outbox, [])

    def test_valid_to_invalid_cc(self):
        """Test with a valid to and an invalid cc the cc is discarded"""
        mail.outbox = []

        message = message_maker([self.valid_address], cc=[self.banned_address])

        result = self.backend().send_messages([message])

        self.assertEqual(result, 1)
        self.assertEqual(mail.outbox[0].to, [self.valid_address])

    def test_valid_to_invalid_bcc(self):
        """Test with a valid to and an invalid cc the bcc is discarded"""
        mail.outbox = []

        message = message_maker(
            [self.valid_address], bcc=[self.banned_address])

        result = self.backend().send_messages([message])

        self.assertEqual(result, 1)
        self.assertEqual(mail.outbox[0].to, [self.valid_address])
