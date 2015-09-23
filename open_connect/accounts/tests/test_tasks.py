"""Tests for accounts tasks."""
from datetime import datetime
from unittest import TestCase

from django.conf import settings
from django.utils.timezone import now
from mock import patch
from model_mommy import mommy

from open_connect.accounts.models import Invite
from open_connect.accounts.tasks import (
    render_and_send_invite_email
)
from open_connect.mailer.utils import unsubscribe_url


class TestRenderAndSendInviteEmail(TestCase):
    """Test render_and_send_invite_email"""
    def test_invite_content(self):
        """Verify the email content is correct."""
        invite = mommy.make('accounts.Invite')
        self.assertFalse(invite.notified)

        with patch('open_connect.accounts.tasks.send_email') as mock:
            render_and_send_invite_email(invite.pk)

        call_args = mock.call_args[1]
        self.assertEqual(call_args['email'], invite.email)
        self.assertEqual(call_args['from_email'], settings.DEFAULT_FROM_EMAIL)
        # Confirm that the unsubscribe URL is in the message
        self.assertIn(unsubscribe_url(invite.email), call_args['text'])
        self.assertIn(unsubscribe_url(invite.email), call_args['html'])

        invite = Invite.objects.get(pk=invite.pk)
        self.assertIsInstance(invite.notified, datetime)

    def test_no_duplicate_sends(self):
        """If the invite notification has already been sent, do nothing."""
        # pylint: disable=assignment-from-none
        invite = mommy.make('accounts.Invite', notified=now())
        with patch('open_connect.accounts.tasks.send_email') as mock:
            response = render_and_send_invite_email(invite.pk)
        self.assertIsNone(response)
        self.assertFalse(mock.called)
