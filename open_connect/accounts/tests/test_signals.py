"""Test for Accounts signals"""
from allauth.account.models import EmailAddress
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy

from open_connect.accounts.models import User
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class TestEmailChangeReceiver(ConnectTestMixin, TestCase):
    """Test the 'primary email has changed' receiver"""
    def test_user_email_changed(self):
        """Test that the user's email was changed"""
        user = self.create_user(email='hey_yeah@great.local')
        self.client.login(username=user.email, password='moo')

        mommy.make(
            EmailAddress, user=user, verified=True,
            email='its_ok@meh.local')

        self.client.post(
            reverse('account_email'),
            {
                'email': 'its_ok@meh.local',
                'action_primary': True
            })


        updated_user = User.objects.get(pk=user.pk)

        self.assertEqual(updated_user.email, 'its_ok@meh.local')
