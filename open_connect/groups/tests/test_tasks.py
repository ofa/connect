"""Tests for group tasks."""
# pylint: disable=invalid-name
from model_mommy import mommy
from django.utils.timezone import now
from django.test import TestCase
from django.conf import settings
from mock import patch

from open_connect.accounts.models import User, Invite
from open_connect.groups import tasks
from open_connect.groups.models import Group, GroupRequest
from open_connect.groups.tasks import (
    add_user_to_group,
    remove_user_from_group,
    invite_users_to_group,
    notify_owners_of_group_request
)
from open_connect.mailer.templatetags.mailing import email_image_max_width
from open_connect.notifications.models import Subscription
from open_connect.connectmessages.models import UserThread
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import ConnectTestMixin
from open_connect.groups import group_member_added, group_member_removed


class TestRemoveUserFromGroup(ConnectTestMixin, TestCase):
    """Tests for remove_user_from_group task."""
    def setUp(self):
        """Setup the tests"""
        self.thread = self.create_thread()
        self.user = self.thread.first_message.sender
        self.group = self.thread.group

    def test_remove_user_from_group_removes_user(self):
        """Test removing a user from a group."""
        self.assertIn(self.group, self.user.groups_joined)
        remove_user_from_group(self.user.pk, self.group.pk)
        self.assertNotIn(self.group, self.user.groups_joined)
        self.assertFalse(
            Subscription.objects.filter(
                user=self.user, group=self.group).exists()
        )

    def test_thread_not_deleted_when_removing_user(self):
        """A thread should have its status changed to deleted."""
        ut = UserThread.objects.get(user=self.user, thread=self.thread)
        ut_id = ut.pk
        ut.delete()
        self.assertFalse(UserThread.objects.filter(pk=ut_id).exists())
        self.assertTrue(
            UserThread.objects.with_deleted().filter(pk=ut_id).exists())

    def test_user_removed_from_inactive_threads(self):
        """
        Test that a user removed from a group can no longer see threads they
        were not personally involved in.
        """
        user_threads = UserThread.objects.filter(user=self.user)
        uninvolved_thread = self.create_thread(group=self.group)
        self.assertTrue(user_threads.filter(thread=self.thread).exists())
        self.assertTrue(user_threads.filter(thread=uninvolved_thread).exists())

        remove_user_from_group(self.user, self.group)

        self.assertTrue(user_threads.filter(thread=self.thread).exists())
        self.assertFalse(user_threads.filter(thread=uninvolved_thread).exists())

    def test_removes_owner(self):
        """Removing an owner from membership should remove their ownership."""
        self.group.owners.add(self.user)
        self.assertIn(self.user, self.group.owners.all())

        remove_user_from_group(self.user, self.group)
        self.assertNotIn(self.user, self.group.owners.all())

    def test_does_not_remove_userthreads_for_other_groups(self):
        """Only delete UserThreads for the group a user is leaving."""
        # Create a new thread and add our user to the thread's group
        thread2 = self.create_thread()
        add_user_to_group(self.user.pk, thread2.group.pk)

        # Remove user from the group created in setup
        remove_user_from_group(self.user.pk, self.group.pk)

        # There should still be a userthread for the group created in this test
        # through thread2.
        self.assertTrue(
            UserThread.objects.filter(user=self.user, thread=thread2).exists())

    def test_fires_removed_from_group_signal(self):
        """
        Test that removing a user to a group fires the correct django signal

        Signal test method found at
        https://stackoverflow.com/questions/3817213/
        """
        def remove_user_group_signal_receiver(**kwargs):
            """Demo signal for testing"""
            # pylint: disable=attribute-defined-outside-init
            self.remove_signal_group = kwargs['group']
            self.remove_signal_user = kwargs['user']
        # Attach our test signal
        group_member_removed.connect(remove_user_group_signal_receiver)

        group = self.create_group()
        user = self.create_user()
        user.add_to_group(group.pk)

        self.assertFalse(hasattr(self, 'remove_signal_group'))
        self.assertFalse(hasattr(self, 'remove_signal_user'))

        remove_user_from_group(user=user, group=group)

        self.assertEqual(self.remove_signal_group, group)
        self.assertEqual(self.remove_signal_user, user)

        group_member_removed.disconnect(
            receiver=remove_user_group_signal_receiver)


class TestAddUserToGroup(ConnectTestMixin, TestCase):
    """Tests for add_user_to_group task."""
    def setUp(self):
        """Setup the tests"""
        self.thread = self.create_thread()
        self.user = self.thread.first_message.sender
        self.group = self.thread.group

    def test_add_user_to_group_adds_user(self):
        """Test adding a user to a group."""
        user = self.create_user()
        group = mommy.make(Group)
        add_user_to_group.delay(user.pk, group.pk)
        self.assertTrue(
            Subscription.objects.filter(user=user, group=group).exists())
        self.assertIn(group, user.groups_joined)

    def test_reactivates_deleted_userthreads(self):
        """Re-joining a group should reactivate old UserThreads."""
        user = self.thread.recipients.first()
        ut = UserThread.objects.get(user=user, thread=self.thread)
        ut_id = ut.pk
        remove_user_from_group(user, self.group)
        add_user_to_group.delay(user.pk, self.group.pk)
        self.assertTrue(UserThread.objects.filter(pk=ut_id).exists())
        self.assertEqual(UserThread.objects.filter(
            user=user, thread=self.thread).count(), 1)

    def test_bails_out_if_user_is_already_member(self):
        """Test that nothing happens if a user is already a member."""
        Subscription.objects.filter(
            user_id=self.user.pk, group=self.group).delete()
        with patch.object(tasks, 'send_system_message') as mock:
            add_user_to_group.delay(
                self.user.pk,
                self.group.pk,
                notification=('test', 'test')
            )
            self.assertEqual(mock.delay.call_count, 0)

    def test_bails_out_with_existing_subscription(self):
        """Test that nothing happens if a user has an existing subscription"""
        user = mommy.make(User)
        group = mommy.make(Group)
        mommy.make(Subscription, user=user, group=group)
        thread = self.create_thread(recipient=user)
        UserThread.objects.filter(
            thread=thread, user=user).update(status='deleted')

        add_user_to_group.delay(user.pk, group.pk)

        with patch.object(tasks, 'send_system_message') as mock:
            add_user_to_group.delay(
                user.pk,
                group.pk,
                notification=('test', 'test')
            )
            self.assertEqual(mock.delay.call_count, 0)

    @patch('open_connect.groups.tasks.send_system_message')
    def test_add_user_to_group_with_notification(self, mock):
        """Test adding to a group with a notification"""
        group = mommy.make(Group)
        subject = 'This is a subject'
        message = 'This is a message'

        add_user_to_group.delay(
            self.user.pk, group.pk, notification=(subject, message))
        self.assertIn(group, self.user.groups_joined)
        self.assertIn(self.user, group.get_members())

        mock.delay.assert_called_with(
            self.user.pk, 'This is a subject', 'This is a message'
        )

    def test_creates_with_default_notification_preference(self):
        """Test adding users to groups when they have an email preference"""
        user_immediate = mommy.make(
            User, group_notification_period='immediate')
        user_daily = mommy.make(User, group_notification_period='daily')
        user_override = mommy.make(User, group_notification_period='daily')

        add_user_to_group.delay(user_immediate.pk, self.group.pk)
        add_user_to_group.delay(user_daily.pk, self.group.pk)
        add_user_to_group.delay(user_override.pk, self.group.pk, period='none')

        self.assertTrue(Subscription.objects.filter(
            user=user_immediate, group=self.group, period='immediate'))
        self.assertTrue(Subscription.objects.filter(
            user=user_daily, group=self.group, period='daily'))
        self.assertTrue(Subscription.objects.filter(
            user=user_override, group=self.group, period='none'))

    @patch('open_connect.groups.tasks.send_system_message')
    def test_add_user_to_group_notifies_owners(self, mock):
        """Adding a user to a group should notify the owners of the group."""
        group = Group.objects.create(name='test')
        # group = mommy.make('groups.Group')
        owner = self.create_superuser()
        group.owners.add(owner)
        add_user_to_group.delay(self.user.pk, group.pk)
        call_args = mock.delay.call_args_list[0][1]
        self.assertEqual(call_args['recipient'], owner.pk)
        self.assertEqual(
            call_args['subject'], u'Your group test has a new member.')
        self.assertIn(
            self.user.full_url, call_args['message_content'])
        self.assertIn(group.full_url, call_args['message_content'])
        self.assertEqual(mock.delay.call_count, 1)

    @patch('open_connect.groups.tasks.send_system_message')
    def test_add_user_to_group_does_not_notify_opted_out_owners(self, mock):
        """Owners who have opted out of join notifications shouldn't get one."""
        group = Group.objects.create(name='test')
        # group = mommy.make('groups.Group')
        owner = self.create_superuser(receive_group_join_notifications=False)
        group.owners.add(owner)
        add_user_to_group.delay(self.user.pk, group.pk)

        self.assertEqual(mock.delay.call_count, 0)

    def test_user_sees_existing_threads(self):
        """Test that a user added to a group can see the existing threads."""
        user = mommy.make(User)
        self.assertFalse(UserThread.objects.filter(user=user).exists())

        add_user_to_group.delay(user.pk, self.group.pk)
        user_threads = UserThread.objects.filter(user=user)
        self.assertTrue(user_threads.exists())
        self.assertTrue(user_threads.filter(
            thread=self.thread, subscribed_email=True).exists())

    def test_fires_added_to_group_signal(self):
        """
        Test that adding a user to a group fires the correct django signal

        Signal test method found at
        https://stackoverflow.com/questions/3817213/
        """
        def add_user_group_signal_receiver(**kwargs):
            """Demo signal for testing"""
            # pylint: disable=attribute-defined-outside-init
            self.add_signal_group = kwargs['group']
            self.add_signal_user = kwargs['user']

        # Attach our test signal
        group_member_added.connect(add_user_group_signal_receiver)

        group = self.create_group()
        user = self.create_user()

        self.assertFalse(hasattr(self, 'add_signal_group'))
        self.assertFalse(hasattr(self, 'add_signal_user'))
        add_user_to_group(user_id=user.pk, group_id=group.pk)

        self.assertEqual(self.add_signal_group, group)
        self.assertEqual(self.add_signal_user, user)

        group_member_added.disconnect(
            receiver=add_user_group_signal_receiver)


class NotifyOwnersOfGroupRequestTest(TestCase):
    """Tests for notify_owners_of_group_request"""
    def setUp(self):
        """Setup the tests"""
        self.user1 = mommy.make(User)
        self.user2 = mommy.make(User)

        sysmessage_patcher = patch(
            'open_connect.groups.tasks.send_system_message')
        self.mocksysmessage = sysmessage_patcher.start()
        self.addCleanup(sysmessage_patcher.stop)

    def test_notify_multiple_owners(self):
        """Test notifying multiple owners"""
        requsting_user = mommy.make(User)
        group = mommy.make(Group)

        self.user1.add_to_group(group.pk)
        group.owners.add(self.user1)
        self.user2.add_to_group(group.pk)
        group.owners.add(self.user2)
        self.mocksysmessage.reset_mock()

        request = mommy.make(GroupRequest, user=requsting_user, group=group)
        notify_owners_of_group_request(request.pk)
        self.assertTrue(self.mocksysmessage.delay.called)
        self.assertEqual(self.mocksysmessage.delay.call_count, 2)

    def test_notify_one_owner(self):
        """Test nofifying one owner (allows us to do more granular testing)"""
        requsting_user = mommy.make(User)
        group = mommy.make(Group)

        self.user1.add_to_group(group.pk)
        group.owners.add(self.user1)

        request = mommy.make(GroupRequest, user=requsting_user, group=group)
        notify_owners_of_group_request(request.pk)

        self.assertTrue(self.mocksysmessage.delay.called)

        call_args = self.mocksysmessage.delay.call_args[0]
        self.assertEqual(call_args[0], self.user1.pk)
        self.assertIn(str(group), call_args[1])
        self.assertIn(str(requsting_user), call_args[2])
        self.assertIn(settings.ORIGIN, call_args[2])


class InviteUsersToGroupTest(ConnectTestMixin, ConnectMessageTestCase):
    """Tests for invite_users_to_group"""
    def setUp(self):
        """Setup the tests"""
        self.newgroup = mommy.make(Group)

        email_patcher = patch(
            'open_connect.accounts.models.render_and_send_invite_email')
        self.mockemailinvite = email_patcher.start()
        self.addCleanup(email_patcher.stop)

        sysmessage_patcher = patch(
            'open_connect.groups.tasks.send_system_message')
        self.mocksysmessage = sysmessage_patcher.start()
        self.addCleanup(sysmessage_patcher.stop)

    def test_adding_existing_users(self):
        """Test adding users that already exist"""
        users = [self.user1.email]
        self.assertFalse(
            self.user1.groups.filter(group=self.newgroup).exists())
        invite_users_to_group(users, self.user1.pk, self.newgroup.pk)
        self.assertTrue(self.mocksysmessage.delay.called_once)
        self.assertTrue(
            self.user1.groups.filter(group=self.newgroup).exists())

    def test_invite_new_users(self):
        """Test 2 invites are created for users that aren't already invited"""
        users = ['newuser1@example.com', 'newuser2@example.com']

        self.assertFalse(
            Invite.objects.filter(email='newuser1@example.com').exists())
        self.assertFalse(
            Invite.objects.filter(email='newuser2@example.com').exists())

        invite_users_to_group(users, self.user1.pk, self.newgroup.pk)
        self.assertEqual(self.mockemailinvite.delay.call_count, 2)

        self.assertTrue(Invite.objects.filter(
            email='newuser1@example.com',
            groups__in=[self.newgroup],
            created_by=self.user1
        ).exists())
        self.assertTrue(Invite.objects.filter(
            email='newuser2@example.com',
            groups__in=[self.newgroup],
            created_by=self.user1
        ).exists())

    def test_add_to_existing_invite(self):
        """Test adding an extra group to an existing invite"""
        invite1 = mommy.make(Invite, notified=now())
        invite2 = mommy.make(Invite)

        users = [invite1.email, invite2.email]

        self.assertFalse(Invite.objects.filter(
            pk=invite1.pk,
            groups__in=[self.newgroup]
        ).exists())
        self.assertFalse(Invite.objects.filter(
            pk=invite2.pk,
            groups__in=[self.newgroup]
        ).exists())

        invite_users_to_group(users, self.user1.pk, self.newgroup.pk)
        # Since one invite was already notified, the call_count should be 1
        self.assertEqual(self.mockemailinvite.delay.call_count, 1)

        self.assertTrue(Invite.objects.filter(
            pk=invite1.pk,
            groups__in=[self.newgroup]
        ).exists())
        self.assertTrue(Invite.objects.filter(
            pk=invite2.pk,
            groups__in=[self.newgroup]
        ).exists())

    def test_users_is_string(self):
        """Test adding users via a string of emails"""
        users = 'afdsafs@example.com, newusfdafser2@example.com'

        self.assertFalse(
            Invite.objects.filter(email='afdsafs@example.com').exists())
        self.assertFalse(
            Invite.objects.filter(email='newusfdafser2@example.com').exists())

        invite_users_to_group(users, self.user1.pk, self.newgroup.pk)
        self.assertEqual(self.mockemailinvite.delay.call_count, 2)

        self.assertTrue(Invite.objects.filter(
            email='afdsafs@example.com',
            groups__in=[self.newgroup],
            created_by=self.user1
        ).exists())
        self.assertTrue(Invite.objects.filter(
            email='newusfdafser2@example.com',
            groups__in=[self.newgroup],
            created_by=self.user1
        ).exists())

    @patch('open_connect.groups.tasks.send_system_message')
    def test_adding_existing_users_notification(self, mock):
        """Test that users who already exist get a customized notification"""
        users = [self.user1.email]

        image = mommy.make(
            'media.Image', image_width='500', image_height='1000')
        group = mommy.make(Group, image=image)
        invite_users_to_group(users, self.user1.pk, group.pk)
        self.assertTrue(mock.delay.called_once)

        message = mock.delay.call_args[0][2]
        group_image_email_version = email_image_max_width(
            image, 300, 'style="margin: 0 auto;"')
        self.assertIn(group_image_email_version, message)
        self.assertIn('GO TO GROUP', message)

        self.assertTrue(
            self.user1.groups.filter(group=group).exists())
