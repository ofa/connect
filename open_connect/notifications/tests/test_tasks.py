"""Tests for notifications celery tasks."""
# pylint: disable=invalid-name
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django.utils.dateparse import parse_datetime
from mock import patch, call
from model_mommy import mommy

from open_connect.connectmessages.models import Message
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.notifications import tasks
from open_connect.notifications.models import Notification
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class TestCreateGroupNotifications(TestCase):
    """Tests for create_group_notifications and create_group_notification."""
    def setUp(self):
        """Setup the test"""
        self.sender = mommy.make('accounts.User')
        self.group = mommy.make('groups.Group')
        self.sender.add_to_group(self.group.pk)
        self.thread = mommy.make('connectmessages.Thread', group=self.group)
        self.message = mommy.make(
            'connectmessages.Message',
            sender=self.sender,
            thread=self.thread
        )
        # Remove any existing notifications created by creating the message
        Notification.objects.filter(message_id=self.message.pk).delete()

    @patch.object(tasks, 'send_immediate_notification')
    def test_create_group_notification(self, mock):
        """Test create_group_notifications."""
        immediate_user = mommy.make('accounts.User')
        immediate_user.add_to_group(self.group.pk)

        # Execute the group notification
        tasks.create_group_notifications(self.message.pk)

        # Confirm that the notification that was created was for user2
        notification = Notification.objects.get(
            recipient=immediate_user, message=self.message)

        # Confirm that a new notification was created
        mock.delay.assert_called_once_with(notification.pk)

    @patch.object(tasks, 'send_immediate_notification')
    def test_no_notification_created_for_none_period(self, mock):
        """If a user's period is none, no notification should be created."""
        none_user = mommy.make('accounts.User')
        none_user.add_to_group(self.group.pk, period='none')

        # Execute the group notification
        tasks.create_group_notifications(self.message.pk)

        # Confirm that no notification was created for user3
        self.assertFalse(
            Notification.objects.filter(
                recipient=none_user, message=self.message).exists()
        )

        # Confirm that send_immediate_notification was not called
        self.assertFalse(mock.delay.called)

    def test_unsubscribed_user_not_added(self):
        """
        Test that a user flagged as 'unsubscribed' does not receive messages
        """
        user = mommy.make('accounts.User', unsubscribed=True)
        user.add_to_group(self.group.pk, period='immediate')
        user.save()

        # Execute the group notification
        tasks.create_group_notifications(self.message.pk)

        # Confirm that no notifications were created
        self.assertFalse(
            Notification.objects.filter(message_id=self.message.pk).exists())

        # Confirm that the unsubscribed user did not get a notification
        self.assertFalse(
            Notification.objects.filter(
                message_id=self.message.pk, recipient=user)
        )


class TestCreateRecipientNotifications(ConnectTestMixin, TestCase):
    """Tests for create_recipient_notifications."""
    def setUp(self):
        """Setup the TestCreateRecipientNotifications TestCase"""
        self.thread = self.create_thread()
        self.message = self.thread.first_message

    def test_notification_created_for_recipient(self):
        """Test create_recipient_notifications."""
        user = mommy.make('accounts.User')
        mommy.make('connectmessages.UserThread', thread=self.thread, user=user)

        tasks.create_recipient_notifications(self.message.pk)

        self.assertTrue(
            Notification.objects.filter(
                recipient=user,
                message_id=self.message.pk,
                consumed=True,
                message=self.message
            ).exists()
        )

    def test_notification_not_created_for_unsubscribed_user(self):
        """Test that an unsubscribed user won't receive a notification"""
        user = mommy.make('accounts.User', unsubscribed=True)
        mommy.make('connectmessages.UserThread', thread=self.thread, user=user)

        tasks.create_recipient_notifications(self.message.pk)

        self.assertFalse(
            Notification.objects.filter(
                recipient=user,
                message=self.message
            ).exists()
        )

    @patch.object(tasks, 'send_immediate_notification')
    def test_sends_immediate_notification(self, mock_send):
        """User's with a default of immediate notifications should get one."""
        delayed_user = self.create_user(direct_notification_period='daily')
        delayed_thread = self.create_thread(
            recipient=delayed_user, direct=True)

        tasks.create_recipient_notifications(
            delayed_thread.first_message.pk)

        self.assertFalse(mock_send.called)

        immediate_user = self.create_user(
            direct_notification_period='immediate')
        immediate_thread = self.create_thread(
            recipient=immediate_user, direct=True)

        tasks.create_recipient_notifications(
            immediate_thread.first_message.pk)

        notification = Notification.objects.get(
            recipient=immediate_user, message=immediate_thread.first_message)
        mock_send.delay.assert_called_once_with(notification.pk)


@patch.object(tasks, 'send_email')
class TestSendImmediateNotification(ConnectMessageTestCase):
    """Tests for send_immediate_notification"""

    @override_settings(BRAND_TITLE='Connect Test')
    def test_called(self, mock):
        """Test to make sure that the emailer was properly called"""
        user = mommy.make('accounts.User')
        notification = mommy.make(
            Notification,
            recipient=user, message=self.message1)

        self.assertFalse(notification.consumed)

        tasks.send_immediate_notification(notification.pk)
        self.assertTrue(
            Notification.objects.get(pk=notification.pk).consumed)
        mock.assert_called_once()

        args = mock.call_args[1]

        # To
        email = args['email']
        self.assertIn(user.email, email)
        self.assertIn(user.get_full_name(), email)

        # From
        from_email = args['from_email']
        self.assertIn(settings.DEFAULT_FROM_ADDRESS, from_email)
        self.assertIn('Connect Test', from_email)
        self.assertIn(self.message1.sender.get_full_name(), from_email)

        # Subject
        subject = args['subject']
        self.assertIn(str(self.message1.thread.group), subject)
        self.assertIn(self.message1.thread.subject, subject)

        # Body (HTML and Plaintext)
        html = args['html']
        plaintext = args['text']
        self.assertIn(self.message1.text, html)
        self.assertIn('Reply', html)
        self.assertIn(self.message1.clean_text, plaintext)

    @override_settings(BRAND_TITLE='Connect Test')
    def test_called_direct_message(self, mock):
        """Test triggering the notification system with a direct message"""
        user = mommy.make('accounts.User')
        notification = mommy.make(
            Notification,
            recipient=user, message=self.directmessage1)

        self.assertFalse(notification.consumed)

        tasks.send_immediate_notification(notification.pk)
        self.assertIsNotNone(
            Notification.objects.get(pk=notification.pk).consumed)
        mock.assert_called_once()

        args = mock.call_args[1]

        # To
        email = args['email']
        self.assertIn(user.email, email)
        self.assertIn(user.get_full_name(), email)

        # From
        from_email = args['from_email']
        self.assertIn(settings.DEFAULT_FROM_ADDRESS, from_email)
        self.assertIn('Connect Test', from_email)
        self.assertIn(self.directmessage1.sender.get_full_name(), from_email)

        # Subject
        subject = args['subject']
        self.assertEqual(self.directmessage1.thread.subject, subject)

        # Body (HTML and Plaintext)
        html = args['html']
        plaintext = args['text']
        self.assertIn(self.directmessage1.text, html)
        self.assertIn('Reply', html)
        self.assertIn(self.directmessage1.clean_text, plaintext)

    def test_includes_unsubscribe_link(self, mock):
        """Ensure that the unsubscribe link is in the email"""
        user = mommy.make('accounts.User')
        notification = mommy.make(
            Notification,
            recipient=user,
            message=self.message1
        )
        tasks.send_immediate_notification(notification.pk)
        mock.assert_called_once()

        args = mock.call_args[1]

        self.assertIn('unsubscribe', args['html'].lower())
        self.assertIn(user.unsubscribe_url, args['html'])
        self.assertIn('unsubscribe', args['text'].lower())
        self.assertIn(user.unsubscribe_url, args['text'])


@patch.object(tasks, 'send_email')
class TestSendDailyDigestNotification(ConnectTestMixin, TestCase):
    """Tests for send_daily_digest_notification"""
    def test_marked_consumed(self, mock):
        """Test to make sure that the notification was marked consumed"""
        user = self.create_user()

        # Create the group and add the user to that group
        group = self.create_group()
        user.add_to_group(group.pk, period='daily')

        thread1 = self.create_thread(group=group)
        message1 = thread1.first_message
        notification1 = user.notification_set.get(message=message1)

        thread2 = self.create_thread(group=group)
        message2 = thread2.first_message
        notification2 = user.notification_set.get(message=message2)

        self.assertFalse(
            Notification.objects.get(pk=notification1.pk).consumed)
        self.assertFalse(
            Notification.objects.get(pk=notification2.pk).consumed)

        tasks.send_daily_digest_notification(user.pk)
        mock.assert_called_once()

        self.assertTrue(
            Notification.objects.get(pk=notification1.pk).consumed)
        self.assertTrue(
            Notification.objects.get(pk=notification2.pk).consumed)

    def test_outgoing_email(self, mock):
        """Test that the digest is properly sent"""
        user = self.create_user()

        group = self.create_group()
        user.add_to_group(group.pk, period='daily')

        thread1 = self.create_thread(group=group)
        thread2 = self.create_thread(group=group)

        tasks.send_daily_digest_notification(user.pk)
        mock.assert_called_once()

        args = mock.call_args[1]

        # To
        email = args['email']
        self.assertIn(user.email, email)
        self.assertIn(user.get_full_name(), email)

        # From
        from_email = args['from_email']
        self.assertIn(settings.DEFAULT_FROM_ADDRESS, from_email)
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, from_email)

        # Subject
        subject = args['subject']
        self.assertIn('2 New Messages', subject)
        days_of_week = [
            'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
            'Saturday'
        ]
        self.assertTrue(any([dayname in subject for dayname in days_of_week]))

        # Body (HTML and Plaintext)
        html = args['html']
        plaintext = args['text']
        self.assertIn(thread1.first_message.text, html)
        self.assertIn(thread2.first_message.text, html)
        self.assertIn('Reply', html)
        self.assertIn(thread1.first_message.clean_text, plaintext)
        self.assertIn(thread2.first_message.clean_text, plaintext)

    def test_no_pending_messages(self, mock):
        """Test that pending messages are never part of a digest"""
        user = self.create_user()

        group = self.create_group()
        user.add_to_group(group.pk, period='daily')

        valid_thread = self.create_thread(group=group)
        pending_thread = self.create_thread(group=group)

        valid_message = valid_thread.first_message

        pending_message = pending_thread.first_message
        pending_message.status = 'pending'
        pending_message.save()

        valid_notification = user.notification_set.get(
            message=valid_message)
        pending_notification = user.notification_set.get(
            message=pending_message)

        tasks.send_daily_digest_notification(user.pk)
        mock.assert_called_once()

        self.assertTrue(
            Notification.objects.get(pk=valid_notification.pk).consumed)
        self.assertFalse(
            Notification.objects.get(pk=pending_notification.pk).consumed)

        args = mock.call_args[1]
        html = args['html']
        self.assertIn(valid_message.text, html)
        self.assertNotIn(pending_message.text, html)

        # Try making the pending notification valid, and test again
        pending_message.status = 'approved'
        pending_message.save()

        tasks.send_daily_digest_notification(user.pk)

        self.assertTrue(
            Notification.objects.get(pk=pending_notification.pk).consumed)

    def test_includes_unsubscribe_link(self, mock):
        """Ensure that the digest includes an unsubscribe link"""
        user = self.create_user()

        thread = self.create_thread()

        mommy.make(
            Notification,
            recipient=user,
            message=thread.first_message,
            subscription__period='daily'
        )

        tasks.send_daily_digest_notification(user.pk)
        mock.assert_called_once()

        args = mock.call_args[1]

        self.assertIn('unsubscribe', args['html'].lower())
        self.assertIn(user.unsubscribe_url, args['html'])
        self.assertIn('unsubscribe', args['html'].lower())
        self.assertIn(user.unsubscribe_url, args['html'])

    def test_no_notifications(self, mock):
        """If there are no notifications, should return None."""
        user = self.create_user()
        # pylint: disable=assignment-from-none
        response = tasks.send_daily_digest_notification(user.pk)
        self.assertIsNone(response)
        self.assertEqual(mock.call_count, 0)


@patch.object(tasks, 'send_daily_digest_notification')
class SendDailyEmailNotifications(ConnectTestMixin, TestCase):
    """Tests for send_daily_email_notifications"""
    def test_called(self, mock):
        """Test that the daily notifications list was properly called"""
        # Mark all existing notifications as sent
        Notification.objects.update(consumed=True)

        group = self.create_group()

        sender = self.create_superuser()
        user1 = self.create_user()
        user2 = self.create_user()
        user3 = self.create_user()

        sender.add_to_group(group.pk)
        user1.add_to_group(group.pk, period='daily')
        user2.add_to_group(group.pk, period='daily')
        user3.add_to_group(group.pk, period='immediate')

        self.create_thread(sender=sender, group=group)

        self.assertEqual(mock.delay.call_count, 0)

        tasks.send_daily_email_notifications()

        self.assertEqual(mock.delay.call_count, 2)

        self.assertIn(call(user1.pk), mock.delay.call_args_list)
        self.assertIn(call(user2.pk), mock.delay.call_args_list)

    def test_unapproved_not_sent(self, mock):
        """Make sure unapproved messages are not sent"""
        # Mark all existing notifications as sent
        Notification.objects.update(consumed=True)

        group = self.create_group()
        user1 = self.create_user()
        user1.add_to_group(group.pk, period='daily')

        thread = self.create_thread(group=group)
        message = thread.first_message

        message.status = 'unapproved'
        message.save()

        tasks.send_daily_email_notifications()

        self.assertEqual(mock.delay.call_count, 0)

        message.status = 'approved'
        message.save()

        tasks.send_daily_email_notifications()

        self.assertEqual(mock.delay.call_count, 1)
        mock.delay.assert_called_once_with(user1.pk)


class ModerationNotificationsTest(ConnectTestMixin, TestCase):
    """A useful mixin for tests that interact with moderator notifications"""
    def setUp(self):
        """Setup the test"""
        # Create a some helper datetimes that relate to our patched now()
        self.one_hour_ago = parse_datetime('2014-09-22T21:21:36.867936+00:00')
        self.two_hours_ago = parse_datetime('2014-09-22T20:21:36.867936+00:00')
        self.one_day_ago = parse_datetime('2014-09-21T22:21:36.867936+00:00')
        self.two_days_ago = parse_datetime('2014-09-20T22:21:36.867936+00:00')

    def generate_pending_message(
            self, group, last_modified_datetime, status='pending'):
        """Generate a message that is pending"""

        # Patch any email notifications about the new message
        with patch.object(tasks, 'send_email'):
            thread = self.create_thread(group=group)

        # This is essentially the only way to force the database to use our
        # fake modified_at instead of this exact moment
        Message.objects.filter(pk=thread.first_message.pk).update(
            status=status, modified_at=last_modified_datetime)
        return thread.first_message


class TestSendModerationNotification(ModerationNotificationsTest):
    """Tests for send_moderation_notification"""
    @patch.object(tasks, 'send_email')
    def test_no_valid_messages(self, mock):
        """Test where the task is called for a user with no recent messages"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        self.generate_pending_message(group, self.two_hours_ago)

        tasks.send_moderation_notification(
            moderator.pk, '2014-09-22T22:00:00+00:00')

        # Confirm that an email was not sent
        self.assertFalse(mock.called)

    @patch.object(tasks, 'send_email')
    def test_valid_message(self, mock):
        """Test where the task is called with one recent message"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        message = self.generate_pending_message(group, self.one_hour_ago)

        tasks.send_moderation_notification(
            moderator.pk, '2014-09-22T22:00:00+00:00')

        call_kwargs = mock.call_args_list[0][1]

        # Confirm the moderator needs to moderate this message
        self.assertIn(message, moderator.messages_to_moderate)
        # Confirm that an email was sent
        self.assertTrue(mock.called)
        self.assertEqual(call_kwargs['email'], moderator.email)
        self.assertEqual(call_kwargs['subject'],
                         'You have 1 new message to moderate on Connect')
        self.assertIn(reverse('mod_admin'), call_kwargs['text'])
        self.assertIn(reverse('mod_admin'), call_kwargs['html'])

    @patch.object(tasks, 'send_email')
    def test_valid_message_flagged(self, mock):
        """Test where the task is called with one recent flagged message"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        message = self.generate_pending_message(
            group, self.one_hour_ago, status='flagged')

        tasks.send_moderation_notification(
            moderator.pk, '2014-09-22T22:00:00+00:00')

        call_kwargs = mock.call_args_list[0][1]

        # Confirm the moderator needs to moderate this message
        self.assertIn(message, moderator.messages_to_moderate)
        # Confirm that an email was sent
        self.assertTrue(mock.called)
        self.assertEqual(call_kwargs['email'], moderator.email)
        self.assertEqual(call_kwargs['subject'],
                         'You have 1 new message to moderate on Connect')
        self.assertIn(reverse('mod_admin'), call_kwargs['text'])
        self.assertIn(reverse('mod_admin'), call_kwargs['html'])

    @patch.object(tasks, 'send_email')
    def test_valid_messages(self, mock):
        """Test where the task is called with multiple recent messages"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        message1 = self.generate_pending_message(group, self.one_hour_ago)
        message2 = self.generate_pending_message(group, self.one_hour_ago)

        tasks.send_moderation_notification(
            moderator.pk, '2014-09-22T22:00:00+00:00')

        call_kwargs = mock.call_args_list[0][1]

        # Confirm the moderator needs to moderate these messages
        self.assertIn(message1, moderator.messages_to_moderate)
        self.assertIn(message2, moderator.messages_to_moderate)

        # Confirm that an email was sent
        mock.assert_called_once()

        self.assertEqual(call_kwargs['email'], moderator.email)
        self.assertEqual(call_kwargs['subject'],
                         'You have 2 new messages to moderate on Connect')
        self.assertIn(reverse('mod_admin'), call_kwargs['text'])
        self.assertIn(reverse('mod_admin'), call_kwargs['html'])

    @patch.object(tasks, 'send_email')
    def test_valid_messages_one_old(self, mock):
        """Test where the task has one recent and one old message"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        message1 = self.generate_pending_message(group, self.one_hour_ago)
        message2 = self.generate_pending_message(group, self.one_day_ago)

        tasks.send_moderation_notification(
            moderator.pk, '2014-09-22T22:00:00+00:00')

        call_kwargs = mock.call_args_list[0][1]

        # Confirm the moderator needs to moderate these messages
        self.assertIn(message1, moderator.messages_to_moderate)
        self.assertIn(message2, moderator.messages_to_moderate)

        self.assertEqual(call_kwargs['email'], moderator.email)
        self.assertEqual(call_kwargs['subject'],
                         'You have 1 new message to moderate on Connect')
        self.assertIn(
            'You have 2 to moderate total', call_kwargs['html'])
        self.assertIn(reverse('mod_admin'), call_kwargs['text'])
        self.assertIn(reverse('mod_admin'), call_kwargs['html'])


class TestSendModerationNotifications(ModerationNotificationsTest):
    """Test the send_moderation_notifications task"""
    def setUp(self):
        """Setup the test"""
        super(TestSendModerationNotifications, self).setUp()
        # Patch now() to something stable
        now_patcher = patch('open_connect.notifications.tasks.now')
        self.mock_now = now_patcher.start()
        self.mock_now.return_value = parse_datetime(
            '2014-09-22T22:21:36.867936+00:00')
        self.addCleanup(now_patcher.stop)

        # Patch send_moderation_notification
        mod_patcher = patch(
            'open_connect.notifications.tasks.send_moderation_notification')
        self.mock_modmessage = mod_patcher.start()
        self.addCleanup(mod_patcher.stop)

    def test_no_recent_messages(self):
        """All pending messages were more than 1 day old"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        message = self.generate_pending_message(group, self.two_days_ago)

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator.messages_to_moderate)
        self.assertFalse(self.mock_modmessage.delay.called)

    def test_one_recent_message(self):
        """At least one message marked pending in the past 24 hours"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        message = self.generate_pending_message(group, self.one_day_ago)

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator.messages_to_moderate)
        self.assertTrue(self.mock_modmessage.delay.called)
        self.mock_modmessage.delay.assert_called_once_with(
            moderator.pk, '2014-09-22T22:00:00+00:00')

    def test_one_recent_message_flagged(self):
        """At least one message flagged in the past 24 hours"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator)

        message = self.generate_pending_message(
            group, self.one_day_ago, status='flagged')

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator.messages_to_moderate)
        self.assertTrue(self.mock_modmessage.delay.called)
        self.mock_modmessage.delay.assert_called_once_with(
            moderator.pk, '2014-09-22T22:00:00+00:00')

    def test_recent_message_non_notification_period(self):
        """Ensure a moderator who is not scheduled to get notified doesn't"""
        group = mommy.make('groups.Group')
        # 6 is a factor of 24, but not a factor of 22 (the hour we're running
        # this task)
        moderator = self.create_user(moderator_notification_period=6)
        group.owners.add(moderator)

        message = self.generate_pending_message(group, self.one_day_ago)

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator.messages_to_moderate)
        self.assertFalse(self.mock_modmessage.delay.called)

    def test_multiple_moderators(self):
        """Test that multiple modeators get their result at the same time"""
        group = mommy.make('groups.Group')
        moderator1 = self.create_user(moderator_notification_period=1)
        moderator2 = self.create_user(moderator_notification_period=1)
        group.owners.add(moderator1)
        group.owners.add(moderator2)

        message = self.generate_pending_message(group, self.one_day_ago)

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator1.messages_to_moderate)
        self.assertIn(message, moderator2.messages_to_moderate)
        self.assertTrue(self.mock_modmessage.delay.called)
        self.assertEqual(self.mock_modmessage.delay.call_count, 2)

    def test_moderator_disables_notifications(self):
        """Test where the moderator doesn't want notifications"""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=0)
        group.owners.add(moderator)

        message = self.generate_pending_message(group, self.two_days_ago)

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator.messages_to_moderate)
        self.assertFalse(self.mock_modmessage.delay.called)

    def test_user_has_moderate_all_messages_perm(self):
        """A user with can_moderate_all_messages should moderate all msgs."""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        self.add_perm(
            moderator, 'can_moderate_all_messages', 'accounts', 'user')

        message = self.generate_pending_message(group, self.one_day_ago)

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator.messages_to_moderate)
        self.assertTrue(self.mock_modmessage.delay.called)
        self.mock_modmessage.delay.assert_called_once_with(
            moderator.pk, '2014-09-22T22:00:00+00:00')

    def test_user_in_group_with_moderate_all_messages_perm(self):
        """A user in a group with can_moderate_all_messages should get all."""
        group = mommy.make('groups.Group')
        moderator = self.create_user(moderator_notification_period=1)
        perm_group = self.create_group()
        permission = Permission.objects.get_by_natural_key(
            'can_moderate_all_messages', 'accounts', 'user')
        perm_group.group.permissions.add(permission)
        perm_group.group.user_set.add(moderator)

        message = self.generate_pending_message(group, self.one_day_ago)

        tasks.send_moderation_notifications()

        self.assertIn(message, moderator.messages_to_moderate)
        self.assertTrue(self.mock_modmessage.delay.called)
        self.mock_modmessage.delay.assert_called_once_with(
            moderator.pk, '2014-09-22T22:00:00+00:00')
