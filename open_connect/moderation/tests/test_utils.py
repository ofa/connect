# -*- coding: utf-8 -*-
"""Tests for the utilities of the moderation app"""
# pylint: disable=invalid-name

from django.contrib.auth import get_user_model
from model_mommy import mommy

from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.moderation.models import MessageModerationAction
from open_connect.moderation.utils import moderate_messages
from open_connect.connectmessages.models import Message, Thread
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class TestModerationAction(ConnectTestMixin, ConnectMessageTestCase):
    """Test the moderation POST endpoint"""
    def setUp(self):
        """Setup the ModerationAction test"""
        super(TestModerationAction, self).setUp()

    def test_moderate_messages(self):
        """Test that messages can be moderated"""
        Message.objects.update(status='pending')

        # Confirm the update has been applied
        self.assertFalse(Message.objects.filter(
            pk=self.message1.pk, status='spam').exists())
        self.assertFalse(Message.objects.filter(
            pk=self.message2.pk, status='approved').exists())
        self.assertFalse(Message.objects.filter(
            pk=self.message3.pk, status='vetoed').exists())

        changes = {
            'spam': [self.message1.pk],
            'approved': [self.message2.pk],
            'vetoed': [self.message3.pk]
        }
        user = self.create_user()
        self.add_perm(user, 'can_moderate_all_messages', 'accounts', 'user')
        total = moderate_messages(changes, user)

        # Intercepting the logger is by far the easiest way to confirm which
        # fields were actually processed
        self.assertEqual(
            MessageModerationAction.objects.filter(
                message__in=[self.message1, self.message2, self.message3]
            ).count(),
            3
        )

        # Confirm correct results
        self.assertTrue(Message.objects.filter(
            pk=self.message1.pk, status='spam').exists())
        self.assertTrue(Message.objects.filter(
            pk=self.message2.pk, status='approved').exists())
        self.assertTrue(Message.objects.filter(
            pk=self.message3.pk, status='vetoed').exists())

        # Confirm the number is correct
        self.assertEqual(total, 3)

    def test_non_superuser_needs_correct_permissions_to_moderate(self):
        """Test that non-superusers need correct permissions for moderation"""
        Message.objects.update(status='pending')

        newuser = mommy.make(get_user_model())
        newuser.add_to_group(self.group2.pk)
        self.group2.owners.add(newuser)

        self.assertIn(self.message3.thread.group, newuser.groups_moderating)
        self.assertNotIn(self.message1.thread.group, newuser.groups_moderating)

        changes = {
            'spam': [self.message1.pk],
            'approved': [self.message3.pk]
        }
        total = moderate_messages(changes, newuser)

        self.assertTrue(
            self.message3.messagemoderationaction_set.filter(
                newstatus='approved').exists()
        )
        self.assertEqual(total, 1)

        # We need to grab message1 from the database again to confirm it has
        # not changed
        message1 = Message.objects.get(pk=self.message1.pk)
        self.assertEqual(message1.status, 'pending')

    def test_moderate_messages_updates_flags(self):
        """Flags should be updated with moderation action."""
        thread1 = self.create_thread()
        thread2 = self.create_thread()
        message1 = thread1.first_message
        message2 = thread2.first_message
        message1.flag(self.normal_user)
        message1.flag(self.staff_user)
        message2.flag(self.normal_user)

        self.assertEqual(
            message1.flags.filter(moderation_action__isnull=True).count(),
            2
        )
        self.assertEqual(
            message2.flags.filter(moderation_action__isnull=True).count(),
            1
        )

        moderate_messages(
            {'approved': [message1.pk, message2.pk]}, self.superuser)

        self.assertFalse(
            message1.flags.filter(moderation_action__isnull=True).exists())
        self.assertFalse(
            message2.flags.filter(moderation_action__isnull=True).exists())

    def test_moderating_updates_total_messages(self):
        """thread.total_messages should be updated when saving."""
        flag_user = self.create_user()
        superuser = self.create_superuser()
        thread_to_approve = self.create_thread()
        thread_to_approve.first_message.flag(flag_user)
        thread_to_approve.total_messages = 0
        thread_to_approve.save()
        thread_to_veto = self.create_thread()
        thread_to_veto.first_message.flag(flag_user)
        thread_to_veto.total_messages = 1
        thread_to_veto.save()

        self.assertEqual(thread_to_approve.total_messages, 0)
        self.assertEqual(thread_to_veto.total_messages, 1)

        moderate_messages(
            {'approved': [thread_to_approve.first_message.pk],
             'veto': [thread_to_veto.first_message.pk]},
            superuser
        )

        thread_to_approve = Thread.objects.get(pk=thread_to_approve.pk)
        thread_to_veto = Thread.objects.get(pk=thread_to_veto.pk)

        self.assertEqual(thread_to_approve.total_messages, 1)
        self.assertEqual(thread_to_veto.total_messages, 0)
