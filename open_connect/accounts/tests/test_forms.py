"""Tests for accounts.forms."""
# pylint: disable=invalid-name
from datetime import timedelta, datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now
from mock import patch
from model_mommy import mommy

from open_connect.accounts import forms
from open_connect.accounts.models import Invite
from open_connect.connectmessages.models import Thread
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.tests.test_utils_mixins import TEST_HTML


User = get_user_model()


class UserFormTest(ConnectMessageTestCase):
    """Tests for UserForm."""
    @patch.object(forms.SanitizeHTMLMixin, 'sanitize_html')
    def test_form_cleans_html(self, mock):
        """Test that text in form is cleaned"""
        form = forms.UserForm({'biography': TEST_HTML}, instance=self.user1)

        # The form will not be valid, but this will still call our cleaner
        form.is_valid()

        mock.assert_called_once_with(TEST_HTML)


class UserAdminFormTest(TestCase):
    """Tests for UserAdminForm"""
    def test_init(self):
        """Test the __init__() method in UserAdminForm"""
        #auth_group = mommy.make('auth.Group')
        #app_group = mommy.make('groups.Group')

        #form = forms.UserAdminForm()

        #self.assertIn(auth_group, form.fields['groups'].queryset)

        # Temporarially we need to include all app groups in the groups field
        #self.assertNotIn(app_group, form.fields['groups'].queryset)


class BanUserFormTest(TestCase):
    """Tests for BanUserForm."""
    def setUp(self):
        """Setup the test"""
        super(BanUserFormTest, self).setUp()
        self.group1 = mommy.make('groups.Group')
        self.normal_user = mommy.make('accounts.User')
        self.normal_user.add_to_group(self.group1.pk)
        self.banned_user = mommy.make('accounts.User')
        self.banned_user.add_to_group(self.group1.pk)
        thread = mommy.make('connectmessages.Thread', group=self.group1)
        self.message1 = mommy.make(
            'connectmessages.Message', sender=self.banned_user, thread=thread)
        self.message1.created_at = now() - timedelta(hours=3)
        self.message1.save()
        self.message2 = mommy.make(
            'connectmessages.Message', sender=self.normal_user, thread=thread)
        self.thread = Thread.objects.get(pk=thread.pk)

    def test_save_first_message_sender_is_banned_user(self):
        """If the first_message is sent by the banned user, just ban them."""
        # Make sure that everything looks right to start
        self.assertEqual(self.thread.first_message, self.message1)
        self.assertEqual(self.thread.latest_message, self.message2)
        self.assertFalse(self.banned_user.is_banned)

        # Submit the form to ban the user
        form = forms.BanUserForm({'user': self.banned_user.pk, 'confirm': True})
        self.assertTrue(form.is_valid())
        form.save()

        # Make sure the latest message hasn't changed
        thread = Thread.objects.get(pk=self.thread.pk)
        self.assertEqual(thread.latest_message, self.message2)

        # Make sure that the user is now banned
        user = User.objects.get(pk=self.banned_user.pk)
        self.assertTrue(user.is_banned)

    def test_save_latest_message_sender_is_banned_user(self):
        """Latest message sent by banned user but not started by them.auth

        This should cause the user to be banned and the latest_message to be
        set to the most recent message not sent by the banned user.
        """
        # Set the existing messages as sent by a normal user
        self.message1.sender = self.normal_user
        self.message1.save()
        self.message2.sender = self.normal_user
        self.message2.created_at = now() + timedelta(seconds=10)
        self.message2.save()

        # Create a couple messages that are sent by the to-be-banned user.
        mommy.make(
            'connectmessages.Message',
            thread=self.thread,
            sender=self.banned_user
        )
        message4 = mommy.make(
            'connectmessages.Message',
            thread=self.thread,
            sender=self.banned_user
        )

        # Make sure the thread looks right to start
        thread = Thread.objects.get(pk=self.thread.pk)
        self.assertEqual(thread.first_message, self.message1)
        self.assertEqual(thread.latest_message, message4)
        self.assertFalse(self.banned_user.is_banned)

        # Submit the form to ban the user
        form = forms.BanUserForm(
            {
                'user': self.banned_user.pk,
                'confirm': True
            })
        self.assertTrue(form.is_valid())
        form.save()

        # Make sure the user is banned
        user = User.objects.get(pk=self.banned_user.pk)
        self.assertTrue(user.is_banned)

        # Make sure latest_message got updated correctly
        thread = Thread.objects.get(pk=self.thread.pk)
        self.assertEqual(thread.latest_message, self.message2)

    def test_save_confirm_is_true_user_gets_banned(self):
        """If confirm is True, ban the user."""
        self.assertFalse(self.banned_user.is_banned)
        # Submit the form to ban the user
        form = forms.BanUserForm(
            {
                'user': self.banned_user.pk,
                'confirm': True
            })
        self.assertTrue(form.is_valid())
        form.save()

        # Make sure the user is banned
        user = User.objects.get(pk=self.banned_user.pk)
        self.assertTrue(user.is_banned)

    def test_save_confirm_is_false_user_does_not_get_banned(self):
        """If confirm is False, don't ban the user."""
        self.assertFalse(self.banned_user.is_banned)
        # Submit the form to ban the user
        form = forms.BanUserForm(
            {'user': self.banned_user.pk, 'confirm': False})
        self.assertTrue(form.is_valid())
        form.save()

        # Make sure the user is banned
        user = User.objects.get(pk=self.banned_user.pk)
        self.assertFalse(user.is_banned)

    @patch.object(forms, 'Thread')
    def test_save_confirm_is_false_threads_not_updated(self, mock_thread):
        """Thread should not be updated is confirm is False."""
        self.assertFalse(self.banned_user.is_banned)
        # Submit the form to ban the user
        form = forms.BanUserForm(
            {'user': self.banned_user.pk, 'confirm': False})
        self.assertTrue(form.is_valid())
        form.save()

        # Make sure Thread wasn't called.
        self.assertEqual(mock_thread.objects.filter.call_count, 0)

        # Make sure that it would be called if confirm is True
        form = forms.BanUserForm(
            {
                'user': self.banned_user.pk,
                'confirm': True
            })
        self.assertTrue(form.is_valid())
        form.save()

        # Make sure Thread is called.
        self.assertEqual(mock_thread.objects.filter.call_count, 1)


class UnBanUserFormTest(ConnectMessageTestCase):
    """Tests for UnBanUserForm."""
    def setUp(self):
        super(UnBanUserFormTest, self).setUp()
        self.banned_user = mommy.make('accounts.User', is_banned=True)
        self.banned_user.add_to_group(self.group1.pk)

    @patch.object(forms, 'Thread')
    def test_save_confirm_is_false_thread_not_updated(self, mock_thread):
        """Thread should not be called if confirm is False."""
        # Make sure Thread isn't called
        form = forms.UnBanUserForm(
            {'user': self.banned_user.pk, 'confirm': False})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(mock_thread.objects.filter.call_count, 0)

        # Make sure call_count would be 1 if confirm is True.
        form = forms.UnBanUserForm(
            {'user': self.banned_user.pk, 'confirm': True})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(mock_thread.objects.filter.call_count, 1)

    def test_save_confirm_is_false_user_not_unbanned(self):
        """Form should unban a user."""
        # Make sure that the user is banned in the first place.
        self.banned_user.is_banned = True
        self.banned_user.save()

        form = forms.UnBanUserForm(
            {'user': self.banned_user.pk, 'confirm': True})
        self.assertTrue(form.is_valid())
        form.save()

        user = User.objects.get(pk=self.banned_user.pk)
        self.assertFalse(user.is_banned)

    def test_save_unbanned_user_sent_most_recent_message(self):
        """Any threads an the user had the latest msg in should be restored."""
        thread = mommy.make('connectmessages.Thread', group=self.group1)
        message1 = mommy.make(
            'connectmessages.Message', sender=self.normal_user, thread=thread)
        message2 = mommy.make(
            'connectmessages.Message', sender=self.banned_user, thread=thread)
        message2.created_at = now() + timedelta(seconds=10)
        message2.save()
        thread = Thread.objects.get(pk=thread.pk)

        # Make sure that the message from the banned user isn't latest_message.
        self.assertEqual(thread.latest_message, message1)

        # Unban the user.
        form = forms.UnBanUserForm(
            {'user': self.banned_user.pk, 'confirm': True})
        self.assertTrue(form.is_valid())
        form.save()

        # The latest message should now be from the formerly banned user.
        thread = Thread.objects.get(pk=thread.pk)
        self.assertEqual(thread.latest_message, message2)


class InviteFormTest(TestCase):
    """Tests for InviteForm."""
    def test_clean_emails_one_email(self):
        """Should return one valid email in a list."""
        form = forms.InviteForm({'emails': 'test@dj.local'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.clean_emails(), ['test@dj.local'])

    def test_clean_emails_multiple_addresses(self):
        """clean_emails should return a list of valid addresses."""
        form = forms.InviteForm(
            {'emails': 'test@dj.local,hi@dj.local,cow,a@dj.local'}
        )
        self.assertTrue(form.is_valid())
        emails = form.clean_emails()
        self.assertItemsEqual(
            emails, ['test@dj.local', 'hi@dj.local', 'a@dj.local'])

    def test_clean_emails_no_valid_addresses(self):
        """Raise ValidationError if no valid addresses are found."""
        with self.assertRaises(ValidationError):
            form = forms.InviteForm({'emails': 'test'})
            self.assertFalse(form.is_valid())
            form.clean_emails()

    @override_settings(CELERY_ALWAYS_EAGER=False)
    def test_save(self):
        """Saving form should create and return a list of invites."""
        form = forms.InviteForm(
            {'emails': 'test@dj.local,test@dj.local,hi@dj.local,a@dj.local'}
        )
        form.created_by = mommy.make('accounts.User', is_superuser=True)
        self.assertTrue(form.is_valid())
        result = form.save()

        # If the form created the correct invites, there should be 3
        self.assertEqual(len(result), 3)

        # Because send_invite is a task, get the updated invite.
        first_result = Invite.objects.get(pk=result[0].pk)
        # Notified datetime should not be set.
        self.assertIsNone(first_result.notified)


class InviteEntryFormTest(TestCase):
    """Tests for the form for using an invite code."""
    def test_clean_invite_code(self):
        """Test that clean_invite_code returns a valid invite object."""
        invite = mommy.make('accounts.Invite')
        form = forms.InviteEntryForm({'invite_code': invite.code})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['invite_code'], invite)

    def test_clean_invite_code_invalid(self):
        """Test that clean_invite_code raises an ValidationError if invalid."""
        form = forms.InviteEntryForm({'invite_code': 'totally invalid'})
        self.assertFalse(form.is_valid())

    def test_save(self):
        """Test the form's save method consumes an invite."""
        invite = mommy.make('accounts.Invite')
        self.assertFalse(invite.consumed_at)
        self.assertFalse(invite.consumed_by)
        form = forms.InviteEntryForm({'invite_code': invite.code})
        self.assertTrue(form.is_valid())
        user = mommy.make('accounts.User')
        form.user_id = user.pk
        form.save()
        invite = Invite.objects.get(pk=invite.pk)
        self.assertTrue(invite.consumed_at)
        self.assertEqual(invite.consumed_by, user)


class TermsAndConductAcceptFormTest(TestCase):
    """Tests for TermsAndConductAcceptForm"""
    def test_valid(self):
        """Test a valid form."""
        form = forms.TermsAndConductAcceptForm(
            {'accept_tos': True, 'accept_ucoc': True, 'next': '/'}
        )
        self.assertTrue(form.is_valid())

    def test_save(self):
        """Test saving the form"""
        user = mommy.make('accounts.User')
        form = forms.TermsAndConductAcceptForm(
            {'accept_tos': 'yes', 'accept_ucoc': 'yes', 'next': '/'}
        )
        self.assertTrue(form.is_valid())
        user = form.save(user.pk)
        self.assertIsInstance(user.tos_accepted_at, datetime)
        self.assertIsInstance(user.ucoc_accepted_at, datetime)
