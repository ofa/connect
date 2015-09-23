"""Tests for the models in the notification app"""
from django.test import TestCase
from model_mommy import mommy

from open_connect.connectmessages.models import Thread, Message, UserThread
from open_connect.notifications.models import Subscription
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class TestSubscription(ConnectTestMixin, TestCase):
    """Tests for the Subscription model"""
    def test_unicode(self):
        """Test the unicode method on the Subscription model"""
        subscription = mommy.make(Subscription)
        self.assertEqual(
            unicode(subscription),
            u'Subscription to {group_name} for {user}.'.format(
                group_name=subscription.group, user=subscription.user)
        )

    def test_save_subscription(self):
        """Test the save method on the Subscription model"""
        group = mommy.make('groups.Group')
        user1 = self.create_user()
        user2 = self.create_user()
        user1.add_to_group(group.pk)
        user2.add_to_group(group.pk)
        subscription = Subscription.objects.get(user=user2, group=group)
        thread = mommy.make(Thread, group=group)
        mommy.make(Message, thread=thread, sender=user1)

        # Confirm that the new userthread was created and the user is
        # subscribed to it
        userthread = UserThread.objects.get(thread=thread, user=user2)
        self.assertTrue(userthread.subscribed_email)

        # Update the subscription period
        subscription.period = 'none'
        subscription.save()

        # Confirm that I'm no longer subscribed to any threads in the group
        userthread2 = UserThread.objects.get(thread=thread, user=user2)
        self.assertFalse(userthread2.subscribed_email)

        # Update the subscription period again
        subscription.period = 'immediate'
        subscription.save()

        # Confirm that I'm again subscribed to the threads in the group
        userthread3 = UserThread.objects.get(thread=thread, user=user2)
        self.assertTrue(userthread3.subscribed_email)
