"""Email backend for Connect"""
# pylint: disable=invalid-name,no-init
import email.utils
import logging

from django.conf import settings
from django.utils.module_loading import import_string

from open_connect.mailer.models import Unsubscribe

LOGGER = logging.getLogger('mailer.backend')

# Connect enforced unsubscribes using a custom email backend. However, we still
# need a more formal Django email backend to inherit from. Instead of forcing
# the use of the `smtp` backend, we can allow custom backends using the
# `ORIGINAL_EMAIL_BACKEND` setting.
EMAIL_BACKEND_STRING = getattr(
    settings,
    'ORIGINAL_EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend')
DefaultBackend = import_string(EMAIL_BACKEND_STRING)


class ConnectMailerBackend(DefaultBackend):
    """Django mailer for Connect"""

    def send_messages(self, email_messages):
        """
        Filters the messages to remove unsubscribed users
        """
        # pylint: disable=unused-variable
        final_messages = []
        for message in email_messages:
            recipients = message.recipients()
            for recipient in recipients:
                name, address = email.utils.parseaddr(recipient)
                if Unsubscribe.objects.address_exists(address):
                    if recipient in message.to:
                        message.to.remove(recipient)
                    if recipient in message.cc:
                        message.cc.remove(recipient)
                    if recipient in message.bcc:
                        message.bcc.remove(recipient)
                    LOGGER.info(
                        u'Email Stopped (Unsub): %s S: %s',
                        recipient, message.subject)

            # If there are any 'to' addresses left, add the message to
            # our internal queue of valid messages
            if message.to:
                final_messages.append(message)

        if final_messages:
            return super(ConnectMailerBackend, self).send_messages(
                final_messages)
        else:
            return 0
