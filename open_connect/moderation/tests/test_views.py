# -*- coding: utf-8 -*-
# pylint: disable=maybe-no-member, invalid-name
"""Tests for the views of the moderation app"""
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from mock import patch
from model_mommy import mommy

from open_connect.moderation import views
from open_connect.connect_core.utils.basetests import ConnectTestMixin


User = get_user_model()


class ModeratorViewTest(ConnectTestMixin, TestCase):
    """Tests for the ModeratorView"""
    def test_unauthorized_user_raises_404(self):
        """Test that an unauthorized user is served a 404."""
        user = self.create_user(password='1234')

        client = Client()
        client.login(username=user.email, password='1234')

        response = client.get(reverse('mod_admin'))
        self.assertEqual(response.status_code, 404)

    def test_non_existent_group_raises_404(self):
        """Test that loading view with a bad group raises a 404."""
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('mod_bygroup', kwargs={'group': 9999999999}))
        self.assertEqual(response.status_code, 404)

    def test_contains_pending_messages(self):
        """Test that messages that should appear do appear in queue."""
        group = mommy.make('groups.Group', moderated=True)
        thread = self.create_thread(group=group)

        superuser = self.create_superuser()
        self.client.login(username=superuser.email, password='moo')
        response = self.client.get(reverse('mod_admin'))
        self.assertContains(response, thread.first_message.snippet)

    def test_limited_to_single_group_if_specified(self):
        """If a group is specified, results should be limited to that group."""
        group1 = mommy.make('groups.Group', moderated=True)
        thread1 = self.create_thread(group=group1)
        group2 = mommy.make('groups.Group', moderated=True)
        thread2 = self.create_thread(group=group2)

        superuser = self.create_superuser()
        self.client.login(username=superuser.email, password='moo')
        response = self.client.get(
            reverse('mod_bygroup', kwargs={'group': group1.pk}))
        self.assertContains(response, thread1.first_message.snippet)
        self.assertNotContains(response, thread2.first_message.snippet)


class SubmitViewTest(ConnectTestMixin, TestCase):
    """Tests for SubmitView."""
    def setUp(self):
        """Setup the SubmitViewTest TestCase"""
        self.superuser = self.create_superuser()
        self.client.login(username=self.superuser.email, password='moo')

    @classmethod
    def setUpClass(cls):
        """Setup the SubmitViewTest class"""
        super(SubmitViewTest, cls).setUpClass()
        cls.valid_form_data = {
            'message-1': 'spam',
            'message-2': 'approved',
            'message-3': 'vetoed'
        }

    def test_normal_user_non_owner_returns_404(self):
        """A normal user that is not an owner shouldn't have access."""
        user = self.create_user()
        client = Client()
        client.login(username=user.email, password='moo')
        response = client.post(reverse('mod_submit'))
        self.assertEqual(response.status_code, 404)

    def test_normal_user_owner(self):
        """A normal user who owns a group should have access."""
        user = self.create_user()
        mommy.make('groups.Group', moderated=True, owners=[user])
        client = Client()
        client.login(username=user.email, password='moo')
        response = client.post(reverse('mod_submit'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            'No Messages Updated',
            response.cookies['messages'].value
        )

    def test_superuser(self):
        """Superusers have access."""
        response = self.client.post(reverse('mod_submit'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            'No Messages Updated',
            response.cookies['messages'].value
        )

    def test_get_not_allowed(self):
        """GET is not a valid method."""
        response = self.client.get(reverse('mod_submit'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('mod_admin'))

    @patch.object(views, 'messages')
    def test_no_changes(self, mock_messages):
        """
        Test when no changes are made
        Ensure that a "No messages changed" message is sent when the moderation
        functions return 0
        """
        self.client.post(reverse('mod_submit'))
        self.assertIn(
            'No Messages Updated', mock_messages.warning.call_args[0][1])

    @patch.object(views, 'messages')
    @patch('open_connect.moderation.views.moderate_messages')
    def test_one_change(self, mock_moderate, mock_messages):
        """Test that moderate_messages returns number of messages changed."""
        mock_moderate.return_value = 1
        response = self.client.post(reverse('mod_submit'), self.valid_form_data)
        self.assertTrue(mock_moderate.called)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            'Updated 1 Message', mock_messages.success.call_args[0][1])

    @patch.object(views, 'messages')
    @patch('open_connect.moderation.views.moderate_messages')
    def test_two_changes(self, mock_moderate, mock_messages):
        """Test that moderate_messages returns number of messages changed."""
        mock_moderate.return_value = 2
        response = self.client.post(reverse('mod_submit'), self.valid_form_data)
        self.assertTrue(mock_moderate.called)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            'Updated 2 Messages', mock_messages.success.call_args[0][1])

    def test_redirects_to_next(self):
        """Test that moderate_messages redirects to next."""
        response = self.client.post(
            reverse('mod_submit'), {'next': '/redirecttest/'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/redirecttest/', response['location'])

    @patch('open_connect.moderation.views.moderate_messages')
    def test_moderate_message(self, mock):
        """Moderate messages test."""
        expected_call = {
            1: 'spam',
            2: 'approved',
            3: 'vetoed'
        }
        self.client.post(
            reverse('mod_submit'), self.valid_form_data)
        self.assertTrue(mock.called)
        self.assertTrue(mock.called_with(expected_call, self.superuser))

    @patch('open_connect.moderation.views.moderate_messages')
    def test_bad_form_data(self, mock):
        """Test moderate_messages with bad form data."""
        dummy_data = {
            # Test non-interger
            'message-abcd': 'spam',
            # Test correctly formatted
            'message-2': 'approved',
            # Test lack of dash
            'message3': 'spam',
            # Test multiple dashes including interger
            'message-4-100': 'approved',
            # Test double dashes
            'message--5': 'approved',
            # Test unavailable option
            'message-6': 'notanoption',
            # Test does not start with message
            'essage-7': 'approved',
            # Test all interger
            '12345678': 'approved',
            # Test spaces
            'm essage-9': 'approved',
            # Test space at end
            'message-10 ': 'approved',
            # Test Unicode Field name
            u'message-11Ⴟ': 'approved',
            # Test Unicode Value
            'message-12': u'ႿႿ',
            # Test all unicode field/value
            u'ႿႿႿႿႿႿ': 'ႿႿႿႿႿႿ',
            # Another normal/correct version
            'message-14': 'spam',
            # Very large number
            'message-123123123123123123123123123123123123123123123123': 'spam'
        }
        expected_call = {
            2: 'approved',
            4: 'approved',
            14: 'spam',
            123123123123123123123123123123123123123123123123: 'spam'
        }

        response = self.client.post(
            reverse('mod_submit'), dummy_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock.called)
        self.assertTrue(mock.called_with(expected_call, self.superuser))


class ModerationFrequencyUpdateViewTest(ConnectTestMixin, TestCase):
    """Tests for ModerationFrequencyUpdateView."""

    def test_success(self):
        """Test a successful change"""
        superuser = self.create_superuser(moderator_notification_period=1)
        self.client.login(username=superuser.email, password='moo')

        response = self.client.post(
            reverse('mod_notification_frequency'),
            {
                'moderator_notification_period': u'12'
            }
        )

        latest_user = User.objects.get(pk=superuser.pk)
        self.assertEqual(latest_user.moderator_notification_period, 12)

        # Since the user_profile view redirects to the user's UUID-based
        # profile page, we need to expect a 302 status code on the next page
        self.assertRedirects(
            response, reverse('user_profile'), target_status_code=302)
        self.assertIn(
            'moderation frequency has been set',
            response.cookies['messages'].value
        )


class TestFlagLogView(ConnectTestMixin, TestCase):
    """Tests for FlagLogView."""
    def setUp(self):
        """Setup the test"""
        self.user = self.create_user()

    def test_get_queryset_regular_mod(self):
        """Test the get_querset method"""
        moderator = self.create_user()
        group = self.create_group()
        group.owners.add(moderator)

        # Have the test client login as the moderator
        self.login(moderator)

        # Create 2 threads, one of which is in a group the user moderates
        primary_thread = self.create_thread(group=group)
        primary_thread.first_message.flag(self.user)
        hidden_thread = self.create_thread()
        hidden_thread.first_message.flag(self.user)

        # Confirm the moderator does not have global permissions
        self.assertFalse(moderator.global_moderator)

        response = self.client.get(reverse('flag_log'))
        queryset = response.context['flags']

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(
            queryset[0].message_set.first(), primary_thread.first_message)

    def test_get_queryset_superuser(self):
        """Test the get_querset method for superusers"""
        superuser = self.create_superuser()

        # Have the test client login as the superuser
        self.login(superuser)

        first_thread = self.create_thread()
        first_thread.first_message.flag(self.user)
        second_thread = self.create_thread()
        second_thread.first_message.flag(self.user)

        # Confirm the user is not a member of any groups
        self.assertFalse(superuser.groups_moderating.exists())

        # Confirm the user has global permissions
        self.assertTrue(superuser.global_moderator)

        response = self.client.get(reverse('flag_log'))

        superuser_queryset = response.context['flags']
        self.assertEqual(superuser_queryset.count(), 2)

        # As we go in reverse order, the second thread should be first
        self.assertEqual(superuser_queryset[0].message_set.first(),
                         second_thread.first_message)
        self.assertEqual(superuser_queryset[1].message_set.first(),
                         first_thread.first_message)
