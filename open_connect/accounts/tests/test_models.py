"""Tests for accounts.models."""
# pylint: disable=invalid-name, too-many-lines
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now
from mock import patch
from model_mommy import mommy

from open_connect.accounts import models
from open_connect.accounts.models import PermissionDeniedError
from open_connect.groups.models import Group, GroupRequest
from open_connect.notifications.models import Subscription
from open_connect.connectmessages.models import Thread
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import (
    ConnectTestCase, ConnectTestMixin
)


User = get_user_model()


class PatcherMixin(object):
    """Mixin for adding create_patch to a test."""
    # pylint: disable=too-few-public-methods
    def create_patch(self, name):
        """Create a patch matching name."""
        patcher = patch(name)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing


class UserManagerTest(TestCase):
    """Tests for UserManager."""
    def test_create_user(self):
        """Test that creating a user is successful."""
        user = models.User.objects.create_user(
            username='go+1@dj.local', password='bM1!@')
        self.assertEqual(user.email, 'go+1@dj.local')
        self.assertTrue(user.check_password('bM1!@'))
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_user_first_last_email(self):
        """Test creating a user with a first and last name"""
        user = models.User.objects.create_user(
            username='modeltest1@org.local',
            password='abcd123',
            email='MODELTEST123@OrG.LoCaL',
            first_name='John',
            last_name='Smith'
        )

        # Test that first and last name came across
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Smith')

        # Test that the normalized email and username came across
        self.assertEqual(user.email, 'modeltest123@org.local')
        self.assertEqual(user.username, 'modeltest1@org.local')

        # Ensure correct permissions
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_user_removes_unsubscribes(self):
        """Test that creating a user wipes any unsubscribes having his email"""
        from open_connect.mailer.models import Unsubscribe
        mommy.make(Unsubscribe, address='go+unsubtest@dj.local')
        self.assertTrue(Unsubscribe.objects.filter(
            address='go+unsubtest@dj.local').exists())
        models.User.objects.create_user(
            username='go+unsubtest@dj.local', password='bM1!@')
        self.assertFalse(Unsubscribe.objects.filter(
            address='go+unsubtest@dj.local').exists())

    def test_create_user_no_password(self):
        """Test creating a user without a password."""
        user = models.User.objects.create_user(username='go+1@dj.local')
        self.assertEqual(user.email, 'go+1@dj.local')
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = models.User.objects.create_superuser(
            username='b@g.local', password='bM1@')
        self.assertEqual(user.email, 'b@g.local')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)


class UserManagerInviteTest(TestCase):
    """Tests for the user manager"""
    def setUp(self):
        """Setup the UserManagerInviteTest TestCase"""
        self.user = models.User.objects.create(username='b@g.local')

    def test_create_with_invite_no_staff_no_superuser(self):
        """create should consume invite if there is one."""
        invite = models.Invite.objects.create(
            email='alkjfdslakjdsf@dj.local', created_by=self.user)
        user = models.User.objects.create_user(
            username='alkjfdslakjdsf@dj.local')
        invite = models.Invite.objects.get(pk=invite.pk)
        self.assertIsNotNone(invite.consumed_at)
        self.assertEqual(invite.consumed_by, user)

    def test_create_with_invite_is_staff(self):
        """create should set user to staff if invite is set to is_staff."""
        models.Invite.objects.create(
            email='jkldfsjkldsjk@dj.local', created_by=self.user, is_staff=True)
        user = models.User.objects.create_user(
            username='jkldfsjkldsjk@dj.local')
        self.assertTrue(user.is_staff)

    def test_create_with_invite_is_superuser(self):
        """create should set user to superuser if invite.is_superuser."""
        models.Invite.objects.create(
            email='afdavawev@dj.local', created_by=self.user, is_superuser=True)
        user = models.User.objects.create_user(username='afdavawev@dj.local')
        self.assertTrue(user.is_superuser)

    def test_create_with_invite_groups_are_added(self):
        """create should add user to any groups indicated in invite."""
        invite = mommy.make('accounts.Invite', email='testuser@dj.local')
        group1 = mommy.make('groups.Group')
        group2 = mommy.make('groups.group')
        invite.groups.add(group1)
        invite.groups.add(group2)
        user = models.User.objects.create_user(username=invite.email)
        all_groups = user.groups_joined
        self.assertIn(group1, all_groups)
        self.assertIn(group2, all_groups)


class UserTest(ConnectTestMixin, TestCase):
    """Test User model methods."""
    def setUp(self):
        """Setup the test"""
        self.user = self.create_user(
            email='usertest@org.local',
            password='lalala',
            first_name='Jack',
            last_name='Grant'
        )

    def test_get_absolute_url(self):
        """User's absolute url should be their detail page."""
        user = self.user
        user.email = 'kdjfskls@fjdklsfjsdl.com'
        user.save()
        self.assertEqual(
            self.user.get_absolute_url(),
            reverse('user_details', args=[user.uuid])
        )
        user.delete()

    def test_unicode(self):
        """User's unicode conversion should be first name and last initial."""
        self.assertEqual(unicode(self.user), 'Jack G.')

    def test_save_lowercase(self):
        """Test that uppercase emails are converted to lowercase on save"""
        user = self.user
        user.email = 'JackGrant@razzmatazz.local'
        user.save()

        self.assertEqual(
            models.User.objects.get(pk=user.pk).email,
            'jackgrant@razzmatazz.local'
        )

    def test_get_full_name_with_first_and_last(self):
        """User.get_full_name() should return first name and last initial."""
        self.assertEqual(self.user.get_full_name(), 'Jack G.')

    def test_get_full_name_system_user(self):
        """get_full_name should return the system user name for the sys user"""
        with self.settings(SYSTEM_USER_EMAIL=self.user.email):
            self.assertEqual(
                self.user.get_full_name(),
                settings.SYSTEM_USER_NAME
            )

    def test_get_full_name_missing_first_name(self):
        """get_full_name should be first part of email if first name missing."""
        self.user.first_name = ''
        self.assertEqual(self.user.get_full_name(), 'usertest')

    def test_get_full_name_missing_last_name(self):
        """get_full_name should be first name if last name missing."""
        self.user.last_name = ''
        self.assertEqual(self.user.get_full_name(), 'Jack')

    def test_get_full_name_missing_first_and_last_names(self):
        """get_full_name should be first part of email if name is missing."""
        self.user.first_name = ''
        self.user.last_name = ''
        self.assertEqual(self.user.get_full_name(), 'usertest')

    def test_get_short_name_with_first_name(self):
        """get_short_name should be the user's first name."""
        self.assertEqual(self.user.get_short_name(), 'Jack')

    def test_get_short_name_missing_first_name(self):
        """get_short_name is first part of email if first name is missing."""
        self.user.first_name = ''
        self.assertEqual(self.user.get_short_name(), 'usertest')

    @override_settings(ORIGIN='https://theorigin.bo.com')
    def test_full_url(self):
        """Test returning user's profile URL using the origin"""
        user = self.create_user(username='awefawef@fjdklsfjsdl.com')

        correct_url = 'https://theorigin.bo.com{path}'.format(
            path=reverse('user_details', args=[user.uuid]))
        self.assertEqual(
            user.full_url,
            correct_url
        )
        user.delete()

    def test_private_hash(self):
        """Test the private code generator attached to the User model"""
        user = mommy.make(User, email='awesome@example.com')
        first_code = user.private_hash
        user.email = 'awesome2@example.com'
        second_code = user.private_hash

        self.assertIsNotNone(first_code)
        self.assertNotEqual(first_code, second_code)

    def test_system_user(self):
        """system_user should return true for the system user"""
        self.assertFalse(self.user.system_user)
        with self.settings(SYSTEM_USER_EMAIL=self.user.email):
            self.assertTrue(self.user.system_user)

    def test_unsubscribe_url(self):
        """
        Test the URL the user will visit if they need to unsubscribe from
        notices without logging in.
        """
        url = self.user.unsubscribe_url

        self.assertIn('http', url)
        self.assertIn(settings.ORIGIN, url)
        self.assertIn(self.user.private_hash, url)
        self.assertIn(str(self.user.email), url)

    def test_change_notification_url(self):
        """Test that the notification change URL is correct"""
        self.user.save()
        url = self.user.change_notification_url

        self.assertIn('http', url)
        self.assertIn(settings.ORIGIN, url)
        self.assertIn(self.user.private_hash, url)
        self.assertIn(str(self.user.pk), url)

    def test_group_categories(self):
        """Should return a set with categories for groups a user belongs to."""
        gvp_group = mommy.make('groups.Group', category__name='Apples')
        lgbt_group = mommy.make('groups.Group', category__name='Oranges')
        user = mommy.make(User)
        user.save()
        user.add_to_group(gvp_group.pk)
        user.add_to_group(lgbt_group.pk)
        categories = user.group_categories
        self.assertIn('Apples', categories)
        self.assertIn('Oranges', categories)

    def test_get_real_name(self):
        """Should return full name with full last name."""
        self.assertEqual(
            self.user.get_real_name(),
            u'{first_name} {last_name}'.format(
                first_name=self.user.first_name,
                last_name=self.user.last_name
            )
        )

    def test_get_real_name_system_user(self):
        """Should return system user name."""
        self.user.email = settings.SYSTEM_USER_EMAIL
        self.assertEqual(self.user.get_real_name(), settings.SYSTEM_USER_NAME)

    def test_get_real_name_no_last_name(self):
        """Should return the short name."""
        self.user.last_name = ''
        self.assertEqual(self.user.get_full_name(), self.user.get_short_name())


class UserDirectMessagePermissionTest(ConnectTestMixin, TestCase):
    """Tests for User.can_direct_message_user and User.all_user_messageable"""
    def setUp(self):
        """Setup the test"""
        self.recipient = self.create_user()

    def test_staff_messageable(self):
        """Test that direct messages to staff are allowed"""
        user = self.create_user(is_staff=True)
        self.assertTrue(user.all_user_messageable)

        # When a user's staff status is false, disable open messaging
        user.is_staff = False
        self.assertFalse(user.all_user_messageable)

    def test_moderator_messageable(self):
        """Test that direct messages to moderators are allowed"""
        user = self.create_user()
        group = self.create_group()
        group.owners.add(user)

        self.assertTrue(user.can_moderate)
        self.assertTrue(user.all_user_messageable)

    def test_regular_user_not_auto_messageable(self):
        """Test that regular users are not labeled always direct-messageable"""
        user = self.create_user()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.can_moderate)
        self.assertFalse(user.all_user_messageable)

    def test_direct_message_test_superuser(self):
        """Test that superusers can always direct message"""
        user = self.create_superuser()
        self.assertTrue(user.can_direct_message_user(self.recipient))

    def test_direct_message_self(self):
        """Test that users cannot direct message themselves"""
        user = self.create_superuser()
        self.assertFalse(user.can_direct_message_user(user))

    def test_staff_initiate_direct_message(self):
        """Test that staff can initiate direct messages"""
        user = self.create_user(is_staff=True)
        self.assertTrue(user.can_direct_message_user(self.recipient))

    def test_messageable_users_can_receive(self):
        """Test users who can always receive direct messages can be messaged"""
        moderator = self.create_user()
        group = self.create_group()
        group.owners.add(moderator)

        user = self.create_user()

        self.assertTrue(moderator.all_user_messageable)
        self.assertTrue(user.can_direct_message_user(moderator))

    def test_permissioned_initiate_direct_messages(self):
        """Test that users with permissions can inititate direct messages"""
        permission = Permission.objects.get(
            codename='can_initiate_direct_messages')
        user = self.create_user()
        user.user_permissions.add(permission)
        self.assertTrue(user.can_direct_message_user(self.recipient))

    def test_regular_user_cannot_inititate_direct_message(self):
        """Test that a regular user cannot initiate a direct message"""
        user = self.create_user()
        self.assertFalse(user.can_direct_message_user(self.recipient))


class UserCanViewProfileTest(ConnectMessageTestCase):
    """Tests for User.can_view_profile."""
    def setUp(self):
        self.banned_user = mommy.make('accounts.User', is_banned=True)

    def test_can_view_profile_self(self):
        """User can view their own profile."""
        self.assertTrue(self.banned_user.can_view_profile(self.banned_user))

    def test_can_view_profile_not_banned(self):
        """Anyone can view an unbanned profile."""
        self.assertTrue(self.staff_user.can_view_profile(self.normal_user))

    def test_can_view_profile_has_permission(self):
        """Users with the can_view_banned permission can view any profile."""
        user = mommy.make('accounts.User')
        permission = Permission.objects.get(codename='can_view_banned')
        user.user_permissions.add(permission)
        self.assertTrue(user.can_view_profile(self.banned_user))

    def test_can_view_profile_superuser(self):
        """Super users can do whatever they want."""
        self.assertTrue(self.superuser.can_view_profile(self.banned_user))

    def test_can_view_profile_user_is_banned_other(self):
        """Any other user should not be able to see a banned user's profile."""
        self.assertFalse(self.normal_user.can_view_profile(self.banned_user))


class UserDirectMessagesSentSinceTest(ConnectTestMixin, TestCase):
    """Tests for User.direct_messages_sent_since."""
    def test_message_count(self):
        """Should return the correct message count."""
        sender = self.create_user()
        self.create_thread(direct=True, sender=sender)
        self.create_thread(direct=True, sender=sender)
        self.create_thread(direct=True, sender=sender)
        yesterday = now() - timedelta(hours=24)
        self.assertEqual(sender.direct_messages_sent_since(yesterday), 3)


class UserGroupModerationRequestsTest(ConnectTestCase):
    """Tests for UserGroupModerationRequest"""
    # pylint: disable=too-many-instance-attributes
    def setUp(self):
        self.thread1 = mommy.make('connectmessages.Thread')
        self.user1 = models.User.objects.create_user(
            username='mo@dj.local',
            password='lalala',
            first_name='Grace',
            last_name='Grant'
        )
        self.user2 = models.User.objects.create_user(
            username='maeby@dj.local',
            password='lalala',
            first_name='Maeby',
            last_name='Funke'
        )
        self.group_owner = self.user3
        self.group1 = Group.objects.create(name='Test Group')
        self.group1.owners.add(self.group_owner)
        self.unapproved_request = GroupRequest.objects.create(
            user=self.user1, group=self.group1)
        self.approved_request = GroupRequest.objects.create(
            user=self.user2,
            group=self.group1,
            moderated_by=self.group_owner,
            moderated_at=now(),
            approved=True
        )
        self.group2 = Group.objects.create(name='Other Test Group')
        self.non_owner_request = GroupRequest.objects.create(
            user=self.user1, group=self.group2)

    def test_group_join_requests_to_moderate(self):
        """Unapproved requests should be in group_join_requests_to_moderate()"""
        self.assertIn(
            self.unapproved_request,
            self.group_owner.group_join_requests_to_moderate()
        )

    def test_group_join_requests_to_moderate_no_approved_requests_present(self):
        """Approved requests are not in group_join_requests_to_moderate()"""
        self.assertNotIn(
            self.approved_request,
            self.group_owner.group_join_requests_to_moderate()
        )

    def test_group_join_requests_to_moderate_not_an_owner(self):
        """Requests for groups you don't own aren't returned."""
        self.assertNotIn(
            self.non_owner_request,
            self.group_owner.group_join_requests_to_moderate()
        )

    def test_has_group_join_requests_to_moderate(self):
        """If you have requests to moderate, it should return True."""
        self.assertTrue(self.group_owner.has_group_join_requests_to_moderate)

    def test_has_group_join_requests_to_moderate_nothing_to_moderate(self):
        """If you don't have requests to moderate, it should return False."""
        self.unapproved_request.delete()
        self.assertFalse(self.group_owner.has_group_join_requests_to_moderate())

    def test_get_moderation_tasks_has_group_moderation_tasks(self):
        """groups_to_mod in response dict should be true."""
        response = self.group_owner.get_moderation_tasks()
        self.assertTrue(response['groups_to_mod'])

    def test_get_moderation_tasks_has_no_group_moderation_tasks(self):
        """groups_to_mod in response dict should be false."""
        self.unapproved_request.delete()
        cache.clear()
        response = self.group_owner.get_moderation_tasks()
        self.assertFalse(response['groups_to_mod'])


class UserGroupManagementTest(ConnectTestMixin, TestCase):
    """Message moderation test"""
    def test_approved_group_message_not_in_messages_to_moderate(self):
        """Approved messages shouldn't be returned."""
        thread = self.create_thread()
        user = self.create_user()
        user.add_to_group(thread.group)

        self.assertNotIn(thread.first_message, user.messages_to_moderate)

    def test_approved_dm_not_in_messages_to_moderate(self):
        """Approved dms should not be in messages_to_moderate."""
        thread = self.create_thread(direct=True)
        thread.first_message.status = 'approved'
        thread.first_message.save()
        user = self.create_user()

        self.assertNotIn(thread.first_message, user.messages_to_moderate)

    def test_global_moderator(self):
        """Test that users who have the relevant permissions are global mods"""
        user = self.create_user()
        self.assertFalse(user.global_moderator)
        self.add_perm(user, 'can_moderate_all_messages', 'accounts', 'user')

        latest_user = User.objects.get(pk=user.pk)
        self.assertTrue(latest_user.global_moderator)

    def test_has_perm_group_message_in_messages_to_moderate(self):
        """Even if user is not group owner, should see messages to moderate."""
        thread = self.create_thread()
        thread.first_message.status = 'pending'
        thread.first_message.save()

        user = self.create_user()
        self.add_perm(user, 'can_moderate_all_messages', 'accounts', 'user')

        self.assertIn(thread.first_message, user.messages_to_moderate)

    def test_has_perm_dm_in_messages_to_moderate(self):
        """Even if user is not on thread, should see in messages to moderate."""
        dm = self.create_thread(direct=True)
        dm.first_message.status = 'pending'
        dm.first_message.save()

        user = self.create_user()
        self.add_perm(user, 'can_moderate_all_messages', 'accounts', 'user')

        self.assertIn(dm.first_message, user.messages_to_moderate)

    def test_non_group_owner_messages_to_moderate(self):
        """Pending messages should be returned only if user owns the group."""
        thread = self.create_thread()
        thread.first_message.status = 'pending'
        thread.first_message.save()

        user = self.create_user()
        self.assertNotIn(thread.first_message, user.messages_to_moderate)

    def test_group_owner_messages_to_moderate(self):
        """Flagged messages should be in moderation queue."""
        thread = self.create_thread()
        thread.first_message.status = 'pending'
        thread.first_message.save()
        user = self.create_user()
        thread.group.owners.add(user)

        self.assertIn(thread.first_message, user.messages_to_moderate)

    def test_banned_sender_messages_to_moderate(self):
        """Messages sent by banned user should not appear."""
        sender = self.create_user()
        thread = self.create_thread(sender=sender)
        thread.first_message.status = 'pending'
        thread.first_message.save()
        user = self.create_user()
        thread.group.owners.add(user)

        self.assertIn(thread.first_message, user.messages_to_moderate)

        sender.is_banned = True
        sender.save()
        self.assertNotIn(thread.first_message, user.messages_to_moderate)

    def test_has_messages_to_moderate(self):
        """Should return True if there are messages to moderate."""
        Thread.objects.all().delete()
        thread = self.create_thread()
        thread.first_message.status = 'pending'
        thread.first_message.save()

        user = self.create_superuser()
        self.assertTrue(user.has_messages_to_moderate())

    def test_has_messages_to_moderate_nothing_to_moderate(self):
        """Should return False if there aren't messages to moderate."""
        Thread.objects.all().delete()
        self.create_thread()
        user = self.create_superuser()
        self.assertFalse(user.has_messages_to_moderate())

    def test_get_moderation_tasks_has_messages_to_moderate(self):
        """messages_to_mod should be True."""
        Thread.objects.all().delete()
        thread = self.create_thread()
        thread.first_message.status = 'pending'
        thread.first_message.save()

        user = self.create_superuser()
        cache.clear()
        response = user.get_moderation_tasks()
        self.assertTrue(response['messages_to_mod'])

    def test_get_moderation_tasks_no_messages_to_moderate(self):
        """messages_to_mod should be False."""
        Thread.objects.all().delete()
        self.create_thread()
        user = self.create_superuser()
        cache.clear()
        response = user.get_moderation_tasks()
        self.assertFalse(response['messages_to_mod'])

    def test_groups_moderating(self):
        """groups_moderating returns groups you can moderate"""
        group = mommy.make('groups.Group')
        user = self.create_user()
        group.owners.add(user)
        self.assertIn(group, user.groups_moderating)

    def test_user_with_perm_can_moderate(self):
        """Superusers can always moderate groups."""
        user = self.create_user()
        self.add_perm(user, 'can_moderate_all_messages', 'accounts', 'user')
        self.assertTrue(user.can_moderate)

    def test_can_moderate_non_group_owner(self):
        """Non group owners cannot moderate."""
        user = self.create_user()
        self.assertFalse(user.can_moderate)

    def test_can_moderate_group_owner(self):
        """Group owners can moderate."""
        user = self.create_user()
        group = mommy.make('groups.Group')
        group.owners.add(user)
        self.assertTrue(user.can_moderate)

    def test_can_flag_messages(self):
        """Test that can_flag_messages is True for normal users."""
        user = self.create_user()
        self.assertTrue(user.can_flag_messages)

    def test_can_flag_messages_user_is_banned(self):
        """Banned users cannot flag messages. Should fail silently."""
        user = self.create_user(is_banned=True)
        self.assertFalse(user.can_flag_messages)

    def test_groups_joined(self):
        """groups_joined returns groups a user is a member of"""
        group = mommy.make('groups.Group')
        user = self.create_user()
        user.add_to_group(group.pk)
        self.assertIn(group, user.groups_joined)

    def test_groups_joined_user_is_not_member(self):
        """groups_joined does not return groups a user is not a member of."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        self.assertNotIn(group, user.groups_joined)

    def test_cached_groups_joined(self):
        """Should return the same as groups_joined."""
        user = self.create_user()
        groups = mommy.make('groups.Group', _quantity=2)
        for group in groups:
            user.add_to_group(group.pk)
        self.assertQuerysetItemsEqual(
            user.groups_joined,
            user.cached_groups_joined
        )

    def test_cached_groups_joined_multiple_calls(self):
        """Should only call groups_joined once."""
        user = self.create_user()
        with patch('open_connect.accounts.models.cache') as mock_cache:
            groups = mommy.make('groups.Group', _quantity=2)
            for group in groups:
                user.add_to_group(group.pk)

            # pylint: disable=pointless-statement
            user.cached_groups_joined
            user.cached_groups_joined

            self.assertEqual(mock_cache.get.call_count, 1)

    def test_messagable_groups(self):
        """messagable_groups returns groups you can send a message to."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        user.add_to_group(group.pk)

        self.assertIn(group, user.messagable_groups)

    def test_messagable_groups_does_not_contain_non_messageable_groups(self):
        """messagable_groups doesn't return groups you can't message."""
        group = mommy.make('groups.Group')
        user = self.create_user()

        self.assertNotIn(group, user.messagable_groups)

    def test_superuser_can_send_to_non_member_group(self):
        """Super users can send to any group, even if not a member."""
        group = mommy.make(Group)
        user = self.create_superuser()

        self.assertTrue(user.can_send_to_group(group))

    def test_superuser_can_send_to_moderated_group(self):
        """Super users can send to moderated groups."""
        moderated_group = mommy.make(Group, moderated=True)
        user = self.create_superuser()

        self.assertTrue(user.can_send_to_group(moderated_group))

    def test_group_owner_can_send_to_moderated_groups(self):
        """Moderators can send to their own groups."""
        moderated_group = mommy.make(Group, moderated=True)
        group_owner = self.create_user()
        moderated_group.owners.add(group_owner)

        self.assertTrue(group_owner.can_send_to_group(moderated_group))

    def test_group_member_can_send_to_non_moderated_group(self):
        """A group member can send to a group if it is not moderated."""
        group = mommy.make('groups.group')
        user = self.create_user()
        user.add_to_group(group.pk)

        self.assertTrue(user.can_send_to_group(group))

    def test_group_member_can_not_send_to_moderated_group(self):
        """A group member can not send to a moderated group.

        (When a group member sends to a moderated group, it goes to moderation.)
        """
        group = mommy.make('groups.Group', moderated=True)
        user = self.create_user()
        user.add_to_group(group.pk)

        self.assertFalse(user.can_send_to_group(group))

    def test_non_group_member_cannot_send_to_group(self):
        """A user cannot send to a group they aren't a member of."""
        group = mommy.make('groups.Group')
        user = self.create_user()

        self.assertRaises(
            PermissionDeniedError,
            user.can_send_to_group,
            group
        )

    def test_can_send_to_group_if_group_is_falsey(self):
        """If the group is falsey, we're checking a DM."""
        user = self.create_user()
        self.assertTrue(user.can_send_to_group(None))

    def test_whitelisted_user_can_send_to_group_if_group_is_moderated(self):
        """Whitelisted users can send to moderated groups."""
        group = mommy.make('groups.Group', moderated=True)
        user = self.create_user()
        user.add_to_group(group.pk)
        group.whitelist_users.add(user)

        self.assertTrue(user.can_send_to_group(group))

    def test_whitelisted_user_can_send_to_group_if_not_member(self):
        """Whitelist users can send to a group even if they're not a member."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        group.whitelist_users.add(user)

        self.assertTrue(user.can_send_to_group(group))

    # pylint: disable=line-too-long
    @patch('open_connect.accounts.models.group_tasks.notify_owners_of_group_request')
    def test_request_to_join_group(self, mock_group_tasks):
        """Should return the GroupRequest and notify group owners."""
        group = mommy.make('groups.Group', moderated=True)
        user = self.create_user()
        request = user.request_to_join_group(group)
        self.assertIsInstance(request, GroupRequest)
        mock_group_tasks.delay.assert_called_once_with(request.pk)

    # pylint: disable=line-too-long
    @patch('open_connect.accounts.models.group_tasks.notify_owners_of_group_request')
    def test_request_to_join_group_already_requested(self, mock_group_tasks):
        """Should return the GroupRequest and not notify group owners again"""
        group = mommy.make('groups.Group', moderated=True)
        user = self.create_user()
        group_request = GroupRequest.objects.create(user=user, group=group)
        result = user.request_to_join_group(group)
        self.assertEqual(group_request, result)
        self.assertEqual(mock_group_tasks.delay.call_count, 0)

    def test_add_to_group(self):
        """Test adding a user to a group."""
        new_group = mommy.make(Group)
        user = self.create_user()
        user.add_to_group(new_group.pk)
        self.assertIn(user, new_group.get_members())
        subscription = Subscription.objects.get(user=user, group=new_group)
        # Assert that the subscription created has the default period
        self.assertEqual(subscription.period, 'immediate')

    def test_add_to_group_with_extra_kwargs(self):
        """Pass extra kwargs through to Subscription."""
        group = mommy.make(Group)
        user = self.create_user()
        user.add_to_group(group.pk, period='none')
        self.assertIn(user, group.get_members())
        second_subscription = Subscription.objects.get(user=user, group=group)
        # Assert that the extra kwarg was passed along to Subscription
        self.assertEqual(second_subscription.period, 'none')

    @patch('open_connect.accounts.models.group_tasks.add_user_to_group')
    def test_add_to_group_delay(self, mock):
        """Test adding a user to a group with a delay."""
        new_group = mommy.make(Group)
        user = self.create_user()
        user.add_to_group(new_group.pk)
        mock.delay.assert_called_once_with(
            user_id=user.pk,
            group_id=new_group.pk,
            notification=None,
            period=None
        )

    @patch('open_connect.accounts.models.group_tasks.add_user_to_group')
    def test_add_to_group_immediate(self, mock):
        """Test adding a user to a group with no task delay."""
        new_group = mommy.make(Group)
        user = self.create_user()
        user.add_to_group(new_group.pk, immediate=True)
        mock.assert_called_once_with(
            user_id=user.pk,
            group_id=new_group.pk,
            notification=None,
            period=None
        )

    def test_remove_from_group(self):
        """Test removing a user from a group."""
        new_group = mommy.make(Group)
        user = self.create_user()
        user.add_to_group(new_group.pk)

        user.remove_from_group(new_group)
        self.assertNotIn(new_group, user.groups_joined)

    def test_remove_owner_from_group(self):
        """Test removing a group owner from a group."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        user.add_to_group(group.pk)
        group.owners.add(user)

        user.remove_from_group(group)
        self.assertNotIn(group, user.groups_joined)
        self.assertNotIn(user, group.owners.all())

    def test_bulk_unsubscribe(self):
        """Test bulk unsubscribing from open_connect.notifications"""
        group1 = mommy.make('groups.Group')
        group2 = mommy.make('groups.Group')
        user = self.create_user()
        user.add_to_group(group1.pk, period='immediate')
        user.add_to_group(group2.pk)

        user.bulk_unsubscribe()

        self.assertFalse(
            Subscription.objects.filter(
                period='immediate', group__in=[group1, group2], user=user
            ).exists()
        )
        self.assertEqual(
            Subscription.objects.filter(
                period='none', group__in=[group1, group2], user=user).count(),
            2
        )


def add_email_invites_permission(user):
    """Add the accounts.email_invites permission to a user."""
    permission = Permission.objects.get(
        codename='email_invites', content_type__model='invite')
    user.user_permissions.add(permission)
    return user


class InviteTest(ConnectTestMixin, TestCase):
    """Tests for Invite model."""
    def test_clean(self):
        """clean should lowercase email."""
        invite = models.Invite(email='SOMEONE@DJ.local')
        invite.clean()
        self.assertEqual(invite.email, 'someone@dj.local')

    def test_cannot_send_duplicate_invite(self):
        """Invited user should only receive one email notification."""
        user = self.create_superuser()
        invite = mommy.make(models.Invite, created_by=user)

        # pylint: disable=line-too-long
        with patch('open_connect.accounts.models.render_and_send_invite_email') as mock:
            invite.send_invite()

        self.assertTrue(mock.delay.called)

        # Ensure that we can't send another identical invite
        invite.notified = now()
        invite.save()

        # pylint: disable=line-too-long
        with patch('open_connect.accounts.models.render_and_send_invite_email') as mock2:
            invite.send_invite()

        self.assertFalse(mock2.delay.called)

    def test_send_invite_superuser(self):
        """Test the invite sender"""
        user = self.create_superuser()
        self.assertTrue(user.is_superuser)

        invite = mommy.make(models.Invite, created_by=user)
        # pylint: disable=line-too-long
        with patch('open_connect.accounts.models.render_and_send_invite_email') as mock:
            invite.send_invite()

        self.assertTrue(mock.delay.called)

    def test_send_invite_user_has_permission(self):
        """Sending the invite as a user with email_invites permission."""
        user = self.create_user()
        add_email_invites_permission(user)
        self.assertTrue(user.has_perm('accounts.email_invites'))

        invite = mommy.make(models.Invite, created_by=user)
        # pylint: disable=line-too-long
        with patch('open_connect.accounts.models.render_and_send_invite_email') as mock:
            invite.send_invite()

        self.assertTrue(mock.delay.called)

    def test_send_invite_user_does_not_have_permission(self):
        """Sending the invite as a user without email_invites permission."""
        user = self.create_user()
        self.assertFalse(user.has_perm('accounts.email_invites'))

        invite = mommy.make(models.Invite, created_by=user)
        # pylint: disable=line-too-long
        with patch('open_connect.accounts.models.render_and_send_invite_email') as mock:
            invite.send_invite()

        self.assertFalse(mock.delay.called)

    def test_send_invite_user_has_perm_and_is_superuser(self):
        """Sending the invite as a superuser with permission."""
        user = self.create_superuser()
        add_email_invites_permission(user)
        self.assertTrue(user.has_perm('accounts.email_invites'))
        self.assertTrue(user.is_superuser)

        invite = mommy.make(models.Invite, created_by=user)
        # pylint: disable=line-too-long
        with patch('open_connect.accounts.models.render_and_send_invite_email') as mock:
            invite.send_invite()

        self.assertTrue(mock.delay.called)


class TestValidateTwitterHandle(TestCase):
    """Tests for the valid_twitter_handle validator."""
    def test_valid_twitter_handle(self):
        """Should return None if handle is valid."""
        valid_values = ['JackGrant', '1234User', 'Grace_Grant']
        for value in valid_values:
            self.assertIsNone(models.validate_twitter_handle(value))

    def test_invalid_twitter_handle(self):
        """Test an invalid twitter handle format"""
        invalid_values = [
            'http://www.twitter.com/LINCOLN', '@LINCOLN', 'A Lincoln'
        ]
        for value in invalid_values:
            self.assertRaises(
                ValidationError, models.validate_twitter_handle, value=value)


class TestUserAutocomplete(ConnectTestMixin, TestCase):
    """Test UserAutocomplete view."""
    def test_user_is_staff(self):
        """Staff user should see users in response."""
        user = self.create_user(is_staff=True)
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('autocomplete_light_autocomplete',
                    kwargs={'autocomplete': 'UserAutocomplete'})
        )
        self.assertContains(response, user.email)

    def test_user_is_superuser(self):
        """Superuser should see users in response."""
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('autocomplete_light_autocomplete',
                    kwargs={'autocomplete': 'UserAutocomplete'})
        )
        self.assertContains(response, user.email)

    def test_user_is_normal(self):
        """Normal users should not see anything in response."""
        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('autocomplete_light_autocomplete',
                    kwargs={'autocomplete': 'UserAutocomplete'})
        )
        self.assertNotContains(response, user.email)


@patch('open_connect.accounts.models.cache')
class TestUserIsModerator(ConnectTestMixin, TestCase):
    """Tests for User.is_moderator."""
    def test_user_is_moderator(self, mock_cache):
        """Test when user is a moderator."""
        user = self.create_user()
        group = self.create_group()
        group.owners.add(user)

        # Force every cache lookup to miss
        mock_cache.get.return_value = None
        self.assertTrue(user.is_moderator())
        mock_cache.get.assert_any_call(
            '{}is_moderator'.format(user.cache_key))
        mock_cache.set.any_call(
            '{}is_moderator'.format(user.cache_key), True, 3600)

    def test_user_is_not_moderator(self, mock_cache):
        """Test when user is not a moderator."""
        user = self.create_user()

        # Force every cache lookup to miss
        mock_cache.get.return_value = None

        self.assertFalse(user.is_moderator())
        mock_cache.set.assert_any_call(
            '{}is_moderator'.format(user.cache_key), False, 3600)

    def test_cache_is_set(self, mock_cache):
        """Test the cache is empty."""
        user = self.create_user()
        mock_cache.get.return_value = 'PUMPKIN SPICE LATTE'

        self.assertEqual(user.is_moderator(), 'PUMPKIN SPICE LATTE')
        self.assertEqual(mock_cache.set.call_count, 0)
