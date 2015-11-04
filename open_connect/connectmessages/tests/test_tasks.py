"""Tests for connectmessages.tasks."""
# pylint: disable=invalid-name
from django.test import TestCase, override_settings
from mock import patch
from model_mommy import mommy

from open_connect.accounts.models import User
from open_connect.notifications.models import Notification
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connectmessages.models import Message, Thread, UserThread
from open_connect.connectmessages import tasks
from open_connect.connectmessages.tasks import send_message
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class SendMessageTestMixin(object):
    """Mixin class for common test patches in notifications.tasks."""
    # pylint: disable=invalid-name,missing-docstring
    def setUp(self):
        patcher1 = patch(
            'open_connect.notifications.tasks.create_group_notifications.delay')
        self.addCleanup(patcher1.stop)
        self.groupnotify_mock = patcher1.start()

        patcher2 = patch.object(tasks, 'send_message')
        self.addCleanup(patcher2.stop)
        self.groupsendtask_mock = patcher2.start()


class SendGroupMessageTest(
        ConnectTestMixin, SendMessageTestMixin, TestCase):
    """Tests for connectmessages.tasks.send_message."""
    def test_send_new_group_message(self):
        """Test that each step involved in `send_message is called."""
        group = self.create_group()

        # Create 3 users, a sender and 2 recipients. The 2nd recipient should
        # not be subscribed.
        sender = self.create_user()

        recipient1 = self.create_user()

        recipient2 = self.create_user(group_notification_period='none')

        # Add both the sender and recipients to our group
        recipient1.add_to_group(group.pk)
        recipient2.add_to_group(group.pk)

        thread = self.create_thread(
            sender=sender, group=group, create_recipient=False)
        message = thread.first_message

        # Confirm that the send_message call in `Message.save()` was called and
        # our patch caught it
        self.groupsendtask_mock.assert_called_once_with(
            message.pk, False)

        # Confirm that our message has not been marked as sent
        self.assertFalse(message.sent)

        # Confirm that the only UserThread created was the sender
        self.assertTrue(
            thread.userthread_set.filter(user=sender).exists())
        self.assertEqual(thread.userthread_set.count(), 1)

        # Call the task
        send_message(message.pk)

        # Confirm there are now 3 UserThreads (one for each recipient)
        self.assertEqual(thread.userthread_set.count(), 3)

        # Confirm that the UserThread for each user has the correct
        # notification preference
        self.assertTrue(
            thread.userthread_set.get(user=recipient1).subscribed_email)
        self.assertFalse(
            thread.userthread_set.get(user=recipient2).subscribed_email)

        # Confirm the message was marked as sent
        self.assertTrue(Message.objects.get(pk=message.pk).sent)

        # Confirm that `send_message` made it to the
        # `create_group_notifications` step
        self.groupnotify_mock.assert_called_once_with(message.pk)

    def test_send_new_group_message_with_existing_userthreads(self):
        """Confirm that bulk_create properly sends a new group message even if
        an existing UserThread exists for a member.

        As django's `bulk_create()` will pass along a database IntegrityError
        if we attempt to create a 2nd UserThread for an existing user, and we
        cannot use get_or_create with bulk_create, we need to ensure
        'thread' <-> 'user' uniqueness when generating our list of new
        UserThreads to create
        """
        group = self.create_group()
        sender = self.create_user()
        new_recipient = self.create_user()
        existing_recipient = self.create_user()

        # Add the sender and our recipients to the group
        sender.add_to_group(group.pk)
        new_recipient.add_to_group(group.pk)
        existing_recipient.add_to_group(group.pk)

        thread = self.create_thread(
            sender=sender, group=group, create_recipient=False)
        message = thread.first_message

        # Confirm that the send_message call in `Message.save()` was called and
        # our patch caught it
        self.groupsendtask_mock.assert_called_once_with(
            message.pk, False)

        # Create an existing UserThread for the `existing_recipient`
        UserThread(user=existing_recipient, thread=thread).save()

        # Confirm 2 UserThread objects exist. One for the sender, one for our
        # existing recipeint
        self.assertEqual(thread.userthread_set.count(), 2)

        send_message(message.pk)

        # Confirm the message was marked as sent
        self.assertTrue(Message.objects.get(pk=message.pk).sent)

        # Confirm that 3 UserThread objects exist.
        self.assertEqual(thread.userthread_set.count(), 3)

        # Confirm that `send_message` made it to the
        # `create_group_notifications` step
        self.groupnotify_mock.assert_called_once_with(message.pk)

    def test_banned_user_not_sent(self):
        """Confirm that a message sent from a banned user is not sent"""
        group = self.create_group()
        regular_user = self.create_user()
        regular_user.add_to_group(group.pk)

        banned_user = self.create_user(is_banned=True)
        banned_user.add_to_group(group.pk)

        # pylint: disable=line-too-long
        with patch('open_connect.connectmessages.models.tasks.send_message') as mock:
            thread = self.create_thread(sender=banned_user, group=group)
            self.assertEqual(thread.first_message.sender, banned_user)
            mock.assert_called_once_with(thread.first_message.pk, False)

        self.assertFalse(thread.first_message.sent)
        # pylint: disable=assignment-from-none
        result = send_message(thread.first_message.pk, False)
        self.assertEqual(result, None)

        # Re-pull the message from the database to make sure it was updated
        updated_message = Message.objects.get(pk=thread.first_message.pk)
        self.assertTrue(updated_message.sent)

        recipients = thread.recipients.all()
        self.assertIn(banned_user, recipients)
        self.assertNotIn(regular_user, recipients)

    def test_previously_sent_message_not_sent_twice(self):
        """Test that messages aren't queued twice."""
        thread = self.create_thread()
        message = thread.first_message
        message.sent = True
        message.save()

        send_message(message.pk)

        self.assertFalse(self.groupnotify_mock.called)

    def test_group_notification_called(self):
        """
        Test that connectmessages.tasks.create_group_notifications is called.
        """
        sender = self.create_user()
        thread = self.create_thread(sender=sender)
        newmessage = mommy.make(Message, thread=thread, sender=sender)
        send_message(newmessage.pk)
        self.groupnotify_mock.assert_called_with(newmessage.pk)

    def test_marks_unread(self):
        """Test that sending a message to a group marks the thread as unread."""
        group = self.create_group()
        user1 = self.create_user()
        user2 = self.create_user()

        user1.add_to_group(group.pk)
        user2.add_to_group(group.pk)

        thread = self.create_thread(group=group, create_recipient=False)

        # Since we mock-out send_message in `Message.save()` we have to call
        # `send_message` directly to generate userthreads
        send_message(thread.first_message.pk)

        thread.userthread_set.update(read=True)
        self.assertTrue(
            thread.userthread_set.filter(
                read=True, user=user1).exists()
        )
        self.assertTrue(
            thread.userthread_set.filter(
                read=True, user=user2).exists()
        )

        newmessage = mommy.make(Message, thread=thread, sender=user1)

        send_message(newmessage.pk)

        # Author should have their message marked as read
        self.assertTrue(
            thread.userthread_set.filter(
                read=True, user=user1).exists()
        )
        # User 2 should have their message marked as unread
        self.assertTrue(
            thread.userthread_set.filter(
                read=False, user=user2).exists()
        )

    def tests_unarchives(self):
        """Sending a message to an archived thread should unarchive it."""
        group = self.create_group()
        user1 = self.create_user()
        user2 = self.create_user()

        user1.add_to_group(group.pk)
        user2.add_to_group(group.pk)

        thread = self.create_thread(
            group=group, sender=user1, create_recipient=False)

        # Since we mock-out send_message in `Message.save()` we have to call
        # `send_message` directly to generate userthreads
        send_message(thread.first_message.pk)

        thread.userthread_set.update(status='archived')
        self.assertEqual(
            thread.userthread_set.filter(
                status='archived').count(),
            2
        )

        newmessage = mommy.make(Message, thread=thread, sender=user1)
        send_message(newmessage.pk)

        # Author of new message should still have thread archived
        self.assertTrue(
            thread.userthread_set.filter(
                status='archived', user=user1).exists()
        )
        # User 2 should have the thread unarchived
        self.assertTrue(
            thread.userthread_set.filter(
                status='active', user=user2).exists()
        )

    def test_updates_count(self):
        """Test that sending a message updates the message count."""
        user = self.create_user()
        thread = self.create_thread(sender=user)

        original_count = thread.message_set.count()

        for _ in range(0, 5):
            msg = mommy.make(Message, thread=thread, sender=user)

        send_message(msg.pk)

        # Because django caches querysets, we need to request the thread again
        refreshed_thread = Thread.objects.get(pk=msg.thread.pk)

        self.assertEqual(refreshed_thread.total_messages, original_count + 5)


class SendDirectMessageTest(SendMessageTestMixin, ConnectMessageTestCase):
    """Tests for sending messages to individuals."""
    def test_group_notification_not_called(self):
        """Test that group notification task is not called."""
        send_message(self.directmessage1.pk)
        self.assertFalse(self.groupnotify_mock.called)


@override_settings(SYSTEM_USER_EMAIL='systemuser-email@connect.local')
class SendSystemMessageTest(TestCase):
    """Tests for sending a message from the system user"""
    def setUp(self):
        """Setup the system message tests"""
        # The sqlite test runner doesn't run south migrations, so create the
        # user here if it doesn't exist
        User.objects.get_or_create(
            email='systemuser-email@connect.local', defaults={
                'username': 'systemuser-email@connect.local',
                'is_active': True,
                'is_superuser': True
            })

        self.subject = 'This is a subject'
        self.message = 'This is a message'

    def test_send_system_message(self):
        """Test sending a system message"""
        user = mommy.make(User)

        # pylint: disable=line-too-long
        with patch('open_connect.connectmessages.tasks.send_immediate_notification') as mock:
            tasks.send_system_message(user, self.subject, self.message)

        self.assertTrue(UserThread.objects.filter(
            user=user,
            thread__first_message__sender__email='systemuser-email@connect.local',
            thread__subject=self.subject,
            thread__thread_type='direct',
            thread__closed=True
            ).exists())

        notification = Notification.objects.get(recipient=user)
        self.assertEqual(notification.message.text, self.message)

        # Confirm that the `system_message` and `system_thread` properties on
        # the Message and Thread model work.
        self.assertTrue(notification.message.is_system_message)
        self.assertTrue(notification.message.thread.is_system_thread)

        mock.delay.assert_called_once_with(notification.pk)

    def test_send_system_message_user_pk(self):
        """Test sending a system message by passing in a user's primary key"""
        user = mommy.make(User)

        # pylint: disable=line-too-long
        with patch('open_connect.connectmessages.tasks.send_immediate_notification') as mock:
            tasks.send_system_message(user.pk, self.subject, self.message)

        self.assertTrue(UserThread.objects.filter(
            user=user,
            thread__first_message__sender__email='systemuser-email@connect.local',
            thread__subject=self.subject,
            thread__thread_type='direct',
            thread__closed=True
            ).exists())

        notification = Notification.objects.get(recipient=user)
        mock.delay.assert_called_once_with(notification.pk)

    def test_send_system_message_no_notification(self):
        """
        Test sending a system message to a user that has disabled notifications
        """
        user = mommy.make(User, group_notification_period='none')

        # pylint: disable=line-too-long
        with patch('open_connect.connectmessages.tasks.send_immediate_notification') as mock:
            tasks.send_system_message(user, self.subject, self.message)

        self.assertFalse(mock.delay.called)
