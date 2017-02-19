"""Tests for accounts.views."""
# pylint: disable=no-value-for-parameter,maybe-no-member,invalid-name
from datetime import datetime

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import Client, TestCase, RequestFactory
from django.test.utils import override_settings
from mock import patch
from model_mommy import mommy

from open_connect.accounts import views
from open_connect.accounts.models import Invite, User
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.media.tests import (
    get_in_memory_image_file, get_in_memory_image_instance
)
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class UserDetailViewTest(ConnectTestMixin, TestCase):
    """Tests for the user detail view."""
    def setUp(self):
        """Handy things."""
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')

    def test_context_object_name(self):
        """Test that the object name is account."""
        user_detail_view = views.UserDetailView.as_view()
        user = self.create_user()
        self.request.user = user
        response = user_detail_view(self.request, user_uuid=user.uuid)
        self.assertTrue('account' in response.context_data.keys())

    def test_user_property(self):
        """Test that the user property returns the user."""
        view = views.UserDetailView()
        user = self.create_user()
        view.kwargs = {'user_uuid': user.uuid}
        self.assertEqual(view.user, user)

    def test_non_existant_404(self):
        """Test that a UUID that does not exist causes a 404"""
        view = views.UserDetailView()
        view.kwargs = {'user_uuid': 'does-not-exist'}
        with self.assertRaises(Http404):
            # pylint: disable=W0104
            view.user

    def test_direct_message_regular_user(self):
        """
        Test that a regular user cannot send a direct message to regular users
        """
        visitor = self.create_user()
        recipient = self.create_user()
        self.login(visitor)

        self.assertFalse(visitor.can_direct_message_user(recipient))

        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': recipient.uuid}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            reverse(
                'create_direct_message',
                kwargs={
                    'user_uuid': recipient.uuid
                }
            )
        )

    def test_direct_message_staff(self):
        """
        Test that a regular user can direct message staff
        """
        visitor = self.create_user()
        recipient = self.create_user(is_staff=True)
        self.login(visitor)

        self.assertTrue(visitor.can_direct_message_user(recipient))
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': recipient.uuid}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                'create_direct_message',
                kwargs={
                    'user_uuid': recipient.uuid
                }
            )
        )

    def test_direct_message_regular_user_by_staff(self):
        """
        Test that a staff member can send a direct message to regular users
        """
        visitor = self.create_user(is_staff=True)
        recipient = self.create_user()
        self.login(visitor)

        self.assertTrue(visitor.can_direct_message_user(recipient))
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': recipient.uuid}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                'create_direct_message',
                kwargs={
                    'user_uuid': recipient.uuid
                }
            )
        )

    def test_direct_message_regular_user_by_superuser(self):
        """
        Test that a superuser can send a direct message to regular users
        """
        visitor = self.create_user(is_superuser=True)
        recipient = self.create_user()
        self.login(visitor)

        self.assertTrue(visitor.can_direct_message_user(recipient))
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': recipient.uuid}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                'create_direct_message',
                kwargs={
                    'user_uuid': recipient.uuid
                }
            )
        )

    def test_direct_message_regular_user_by_permission(self):
        """
        Test that someone with the correct permission can message a user
        """
        visitor = self.create_user()
        self.add_perm(
            visitor, 'can_initiate_direct_messages', 'accounts', 'user')
        recipient = self.create_user()

        self.login(visitor)

        self.assertTrue(visitor.can_direct_message_user(recipient))
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': recipient.uuid}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                'create_direct_message',
                kwargs={
                    'user_uuid': recipient.uuid
                }
            )
        )

    def test_show_banned_warning_user_is_banned(self):
        """Banned warning should be shown if the user is banned."""
        request_user = self.create_superuser()
        banned_user = self.create_user(is_banned=True)
        self.client.login(username=request_user.email, password='moo')
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': banned_user.uuid}))
        self.assertTrue(response.context['show_banned_warning'])

    def test_show_banned_warning_user_is_not_banned(self):
        """Banned warning should not show if the user is not banned."""
        request_user = self.create_user()
        unbanned_user = self.create_user()
        self.client.login(username=request_user.email, password='moo')
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': unbanned_user.uuid}))
        self.assertFalse(response.context['show_banned_warning'])

    def test_show_banned_warning_to_self_banned(self):
        """Banned warning should not show to the user that is banned."""
        banned_user = self.create_user(is_banned=True)
        self.client.login(username=banned_user.email, password='moo')
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': banned_user.uuid}))
        self.assertFalse(response.context['show_banned_warning'])

    def test_show_banned_warning_to_self_not_banned(self):
        """Banned warning should not show to an unbanned user."""
        unbanned_user = self.create_user()
        self.client.login(username=unbanned_user.email, password='moo')
        response = self.client.get(
            reverse('user_details', kwargs={'user_uuid': unbanned_user.uuid}))
        self.assertFalse(response.context['show_banned_warning'])

    def test_get_context_data(self):
        """Context should have nav_active_item and show_banned_warning."""
        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('user_details',
                    kwargs={'user_uuid': user.uuid})
        )
        context = response.context
        self.assertEqual(context['nav_active_item'], user)
        self.assertEqual(context['show_banned_warning'], False)
        self.assertQuerysetItemsEqual(
            context['groups_joined'], user.groups_joined)

    def test_get_object(self):
        """get_object should return the correct user."""
        view = views.UserDetailView()
        view.request = self.request_factory.get('/')
        user = self.create_user()
        view.request.user = user
        view.kwargs = {'user_uuid': user.uuid}
        self.assertEqual(view.get_object(), user)

    @patch('open_connect.accounts.views.messages')
    def test_get_object_user_is_banned(self, mock_messages):
        """should return the user and add a warning if user is banned."""
        user = mommy.make('accounts.User', is_banned=True)
        view = views.UserDetailView()
        view.request = self.request
        view.request.user = self.create_superuser()
        view.kwargs = {'user_uuid': user.uuid}
        self.assertEqual(view.get_object(), user)
        self.assertEqual(
            mock_messages.warning.call_args_list[0][0][1],
            'This is a banned account.'
        )

    def test_get_object_user_is_banned_no_permission_to_view_profile(self):
        """should raise Http404 if user is banned and you don't have perms."""
        user = mommy.make('accounts.User', is_banned=True)
        view = views.UserDetailView()
        view.request = self.request_factory.get('/')
        view.request.user = self.create_user(is_staff=True)
        view.kwargs = {'user_uuid': user.uuid}
        self.assertRaises(Http404, view.get_object)


class UserUpdateViewTest(ConnectTestMixin, TestCase):
    """Tests for the user update view."""
    def setUp(self):
        """Setup the UserUpdateViewTest TestCase"""
        self.user = self.create_user(password='test')
        self.client.login(username=self.user.username, password='test')

    def test_authenticated_user_own_profile(self):
        """Test that an authenticated user can access their own update view."""
        response = self.client.get(
            reverse('update_user', args=(self.user.uuid,)))
        self.assertEqual(response.context_data['object'], self.user)

    def test_admin_access_view(self):
        """
        Test that admins with the `accounts.change_user` permission can view
        """
        admin_user = self.create_user(password='admintest')
        admin_client = Client()
        admin_client.login(username=admin_user.username, password='admintest')

        unprivlidged_result = admin_client.get(
            reverse('update_user', args=(self.user.uuid,)))
        self.assertEqual(unprivlidged_result.status_code, 404)

        change_user_permission = Permission.objects.get(
            content_type__app_label='accounts', codename='change_user')

        admin_user.user_permissions.add(change_user_permission)

        privlidged_result = admin_client.get(
            reverse('update_user', args=(self.user.uuid,)))
        self.assertEqual(privlidged_result.status_code, 200)
        self.assertContains(privlidged_result, self.user)

    @override_settings(LOGIN_URL=reverse('login'))
    def test_update_anonymous_user(self):
        """Unauthenticated users should be redirected to the login page."""
        client = Client()
        update_url = reverse('update_user', args=(self.user.uuid,))
        response = client.get(update_url)
        self.assertRedirects(
            response,
            '%s?next=%s' % (reverse('login'), update_url)
        )

    def test_with_image(self):
        """Make sure the user's image gets set when it is provided."""
        data = {
            'image': get_in_memory_image_file(),
            'timezone': 'US/Central',
            'group_notification_period': 'none',
            'email': self.user.email
        }
        response = self.client.post(
            reverse('update_user', args=(self.user.uuid,)), data)
        self.assertRedirects(
            response,
            reverse('user_profile'),
            target_status_code=302
        )
        user = User.objects.get(pk=self.user.pk)
        data['image'].seek(0)
        self.assertEqual(user.image.image.read(), data['image'].read())

    def test_clear_image(self):
        """A user's image should be removed if clear is selected."""
        self.user.image = get_in_memory_image_instance(self.user)
        self.user.save()
        data = {
            'image-clear': True,
            'image': None,
            'timezone': 'US/Central',
            'group_notification_period': 'none',
            'email': self.user.email
        }
        response = self.client.post(
            reverse('update_user', args=(self.user.uuid,)), data)
        self.assertRedirects(
            response,
            reverse('user_profile'),
            target_status_code=302
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertIsNone(user.image)

    def test_group_owner_has_receive_group_join_notifications_field(self):
        """A user who owns any groups should see the field."""
        response = self.client.get(
            reverse('update_user', args=(self.user.uuid,)))
        self.assertNotIn(
            'receive_group_join_notifications',
            response.context['user_form'].fields.keys()
        )

    def test_non_group_owner_does_not_have_receive_group_join_field(self):
        """A user who owns no groups should not see the field."""
        user = self.create_user()
        group = mommy.make('groups.Group')
        group.owners.add(user)
        client = Client()
        client.login(username=user.email, password='moo')
        response = client.get(
            reverse('update_user', args=(user.uuid,)))
        self.assertIn(
            'receive_group_join_notifications',
            response.context['user_form'].fields.keys()
        )

    def test_update_staff_no_permission(self):
        """Only users with the permission should see the staff change toggle"""
        regular_admin = self.create_user()
        self.add_perm(
            regular_admin, 'change_user', 'accounts', 'user')

        regular_client = Client()
        regular_client.login(username=regular_admin.email, password='moo')

        user = self.create_user()

        response = regular_client.get(
            reverse('update_user', args=(user.uuid,)))
        self.assertNotIn(
            'is_staff',
            response.context['user_form'].fields.keys()
        )

    def test_update_staff_privlidged(self):
        """Those with the relevant permission can change staff status"""
        privlidged_admin = self.create_user()
        self.add_perm(
            privlidged_admin, 'change_user', 'accounts', 'user')
        self.add_perm(
            privlidged_admin, 'can_modify_staff_status', 'accounts', 'user')

        privlidged_client = Client()
        privlidged_client.login(
            username=privlidged_admin.email, password='moo')

        user = self.create_user()

        response = privlidged_client.get(
            reverse('update_user', args=(user.uuid,)))
        self.assertIn(
            'is_staff',
            response.context['user_form'].fields.keys()
        )

    def test_update_staff_regular_user(self):
        """Test that regular users cannot update their own staff status"""
        user = self.create_user()
        client = Client()
        client.login(username=user.email, password='moo')

        response = client.get(
            reverse('update_user', args=(user.uuid,)))
        self.assertNotIn(
            'is_staff',
            response.context['user_form'].fields.keys()
        )


class UpdateUserPermissionViewTest(ConnectTestMixin, TestCase):
    """Tests for UpdateUserPermissionView"""
    def setUp(self):
        """Handy things."""
        self.request_factory = RequestFactory()

        # Add 2 permissions to the test, one valid and visible, one hidden
        demo_content_type = ContentType.objects.create(
            app_label='demo-app-label', model='DemoModel')

        self.valid_permission = mommy.make(
            Permission,
            codename='viewable-permission',
            name='Viewable Permission',
            content_type=demo_content_type)
        self.hidden_permission = mommy.make(
            Permission,
            codename='hidden-permission',
            name='Hidden Permission',
            content_type=demo_content_type)

        # Create a view class that contains those permissions
        self.view_class = views.UpdateUserPermissionView
        self.view_class.editable_permissions = (
            ('demo-app-label', 'viewable-permission'),
        )

    def tearDown(self):
        """
        Tear down the test

        Cleanup the test by deleting the test permissions, then verify the
        cleanup
        """
        self.valid_permission.delete()
        self.hidden_permission.delete()
        self.assertNotIn(self.valid_permission, Permission.objects.all())
        self.assertNotIn(self.hidden_permission, Permission.objects.all())

    def test_no_impersonation(self):
        """Test that the view will reject those actively impersonating"""
        # Create a user who is actively impersonating another user
        user = self.create_user()
        user.impersonating = True

        # Create a request
        request = self.request_factory.get('/')
        request.user = user

        # Instead of testing the dispatch() method directly or creating a
        # django test client that is both logged in and impersonating, we can
        # pass a pre-made request directly into the view.
        with self.assertRaises(PermissionDenied):
            self.view_class.as_view()(request)

    def test_get_queryset(self):
        """
        Test the view's get_queryset() method

        Test that neither the requesting User nor a superuser User are in the
        queryset of User objects returned by the view's get_queryset()
        """
        requesting_user = self.create_user()
        regular_user = self.create_user()
        superuser = self.create_superuser()

        view = self.view_class()
        view.request = self.request_factory.get('/')
        view.request.user = requesting_user

        queryset = view.get_queryset()

        # The regular user should be in the queryset
        self.assertIn(regular_user, queryset)

        # Superusers cannot be in the possible queryset
        self.assertNotIn(superuser, queryset)

        # The requesting user cannot be in the possible queryset
        self.assertNotIn(requesting_user, queryset)

    def test_get_editable_permissions(self):
        """
        Test the `get_editable_permissions` method on the view.
        """
        view = self.view_class()

        editable_permissions_queryset = view.get_editable_permissions()

        self.assertEqual(editable_permissions_queryset.count(), 1)
        self.assertIn(self.valid_permission, editable_permissions_queryset)
        self.assertNotIn(self.hidden_permission, editable_permissions_queryset)

    def test_get_permissions_queryset(self):
        """
        Test the get_permissions_queryset() method.
        """
        view = self.view_class()
        view.request = self.request_factory.get('/')
        view.request.user = self.create_user()

        # Create a new "target" user, who is the user the view will be set to
        # edit during a regular request.
        target_user = self.create_user()
        view.object = target_user

        # Get the existing queryset of changeable permissions. This should only
        # include permissions set in the `view.editable_permissions` attribute.
        permissions_queryset = view.get_permissions_queryset()

        self.assertEqual(permissions_queryset.count(), 1)
        self.assertIn(self.valid_permission, permissions_queryset)
        self.assertNotIn(self.hidden_permission, permissions_queryset)

        # Add the hidden permission to the user's list of permissions. This
        # should cause the hidden permission to appear in the queryset
        target_user.user_permissions.add(self.hidden_permission)

        # Re-generate a queryset of editable views
        extended_permissions_queryset = view.get_permissions_queryset()

        self.assertEqual(extended_permissions_queryset.count(), 2)
        self.assertIn(self.valid_permission, extended_permissions_queryset)
        self.assertIn(self.hidden_permission, extended_permissions_queryset)

    def test_get_form(self):
        """
        Test the `get_form` method for users with and without extra permissions
        """
        admin = self.create_superuser()
        self.client.login(username=admin.email, password='moo')

        # Ensure that by default 'Viewable Permission' is found in the form
        # field and 'Hidden Permission' is not
        user = self.create_user()

        response = self.client.get(
            reverse('update_user_permissions', args=[user.uuid]))
        form = response.context['form']

        user_permissions_field = form['user_permissions']
        self.assertIn(u'Viewable Permission', unicode(user_permissions_field))
        self.assertNotIn(u'Hidden Permission', unicode(user_permissions_field))

        # Ensure that if a user has 'Hidden Permission' it is displayed in the
        # form field
        user.user_permissions.add(self.hidden_permission)

        expanded_response = self.client.get(
            reverse('update_user_permissions', args=[user.uuid]))
        expanded_form = expanded_response.context['form']

        expanded_user_permissions_field = expanded_form['user_permissions']
        self.assertIn(
            u'Viewable Permission', unicode(expanded_user_permissions_field))
        self.assertIn(
            u'Hidden Permission', unicode(expanded_user_permissions_field))


class UserProfileRedirectTest(ConnectTestMixin, TestCase):
    """Tests for the user profile redirect view."""
    def test_redirects_to_user_details(self):
        """User profile should redirect to user detais."""
        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(reverse('user_profile'))
        self.assertRedirects(
            response,
            reverse('user_details', args=[user.uuid]),
        )

    @override_settings(LOGIN_URL=reverse('login'))
    def test_anonymous_user(self):
        """Unauthenticated user should be redirected to login."""
        client = Client()
        user_profile_url = reverse('user_profile')
        response = client.get(user_profile_url)
        self.assertRedirects(
            response,
            '%s?next=%s' % (reverse('login'), user_profile_url)
        )


class InviteCreateViewTest(ConnectTestMixin, TestCase):
    """Tests for InviteCreateView."""
    def setUp(self):
        """Handy things."""
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')

    def test_get_success_url(self):
        """get_success_url should return the URL of the invite list page."""
        view = views.InviteCreateView()
        view.request = self.request
        result = view.get_success_url()
        self.assertEqual(result, reverse('invites'))

    def test_form_valid(self):
        """form_valid should set created_by to the current user."""
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        group = mommy.make('groups.Group')
        response = self.client.post(
            reverse('create_invite'),
            {'emails': 'testuser@dj.local', 'groups': [group.pk]}
        )

        invite = Invite.objects.get(email='testuser@dj.local')
        self.assertEqual(invite.created_by, user)
        self.assertRedirects(response, reverse('invites'))

    def test_get_form_non_superuser(self):
        """get_form should remove is_superuser from form and update groups."""
        user = self.create_user(is_staff=True)
        permission = Permission.objects.get_by_natural_key(
            'add_invite', 'accounts', 'invite')
        user.user_permissions.add(permission)
        self.client.login(username=user.email, password='moo')
        response = self.client.get(reverse('create_invite'))
        form = response.context['form']

        self.assertNotIn('is_superuser', form.fields.keys())
        self.assertIn('is_staff', form.fields.keys())
        self.assertQuerysetItemsEqual(
            form.fields['groups'].queryset, user.groups.all())

    def test_get_form_non_staff(self):
        """get_form should remove superuser & staff fields and update groups."""
        user = self.create_user()
        permission = Permission.objects.get_by_natural_key(
            'add_invite', 'accounts', 'invite')
        user.user_permissions.add(permission)
        self.client.login(username=user.email, password='moo')
        response = self.client.get(reverse('create_invite'))
        form = response.context['form']
        self.assertNotIn('is_superuser', form.fields.keys())
        self.assertNotIn('is_staff', form.fields.keys())
        self.assertQuerysetItemsEqual(
            form.fields['groups'].queryset, user.groups.all())

    def test_get_form_superuser(self):
        """get_form should have all fields and all groups."""
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(reverse('create_invite'))
        form = response.context['form']
        self.assertIn('is_superuser', form.fields.keys())
        self.assertIn('is_staff', form.fields.keys())
        self.assertQuerysetItemsEqual(
            form.fields['groups'].queryset, Group.objects.all())


class InviteListViewTest(ConnectTestMixin, TestCase):
    """Tests for InviteListView."""
    def test_query(self):
        """Test searching."""
        user = self.create_superuser()
        find_me = Invite.objects.create(email='hi@dj.local', created_by=user)
        dont_find_me = Invite.objects.create(
            email='bye@dj.local', created_by=user)
        self.client.login(username=user.email, password='moo')
        response = self.client.get(reverse('invites'), {'q': 'hi'})
        self.assertIn(find_me, response.context['invites'])
        self.assertNotIn(dont_find_me, response.context['invites'])


class BanUnBanViewBaseTest(ConnectMessageTestCase):
    """Tests for BanUnBanViewBase."""
    def test_user_property(self):
        """Test that the correct user is returned."""
        view = views.BanUnBanViewBase()
        view.kwargs = {'user_uuid': self.normal_user.uuid}
        self.assertEqual(view.user, self.normal_user)

    def test_get_initial(self):
        """Test that the user is added to the form's initial data."""
        view = views.BanUnBanViewBase()
        view.kwargs = {'user_uuid': self.normal_user.uuid}
        self.assertEqual(view.get_initial()['user'], self.normal_user)

    def test_get_context_data(self):
        """Test that the user is added to the context."""
        view = views.BanUnBanViewBase()
        view.kwargs = {'user_uuid': self.normal_user.uuid}
        self.assertEqual(view.get_context_data()['account'], self.normal_user)

    def test_get_success_url(self):
        """Test that the success url is the user's profile."""
        view = views.BanUnBanViewBase()
        view.kwargs = {'user_uuid': self.normal_user.uuid}
        self.assertEqual(
            view.get_success_url(),
            reverse('user_details', kwargs={'user_uuid': self.normal_user.uuid})
        )


class BanUserViewTest(ConnectMessageTestCase):
    """Tests for BanUserView."""
    def test_form_valid_confirm(self):
        """Test that a user is banned when confirm=True."""
        user = mommy.make('accounts.User', is_banned=False)
        self.assertFalse(user.is_banned)
        response = self.client.post(
            reverse('ban_user', kwargs={'user_uuid': user.uuid}),
            {'user': user.pk, 'confirm': 1}
        )
        self.assertRedirects(
            response, reverse('user_details', kwargs={'user_uuid': user.uuid}))
        user = User.objects.get(pk=user.pk)
        self.assertTrue(user.is_banned)

    def test_form_valid_not_confirmed(self):
        """Test that a user is not banned when confirm=False"""
        user = mommy.make('accounts.User', is_banned=False)
        self.assertFalse(user.is_banned)
        response = self.client.post(
            reverse('ban_user', kwargs={'user_uuid': user.uuid}),
            {'user': user.pk}
        )
        self.assertRedirects(
            response, reverse('user_details', kwargs={'user_uuid': user.uuid}))
        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.is_banned)


class UnBanUserViewTest(ConnectMessageTestCase):
    """Tests for UnBanUserView."""
    def test_form_valid_confirm(self):
        """Test that a user is unbanned when confirm=True."""
        user = mommy.make('accounts.User', is_banned=True)
        self.assertTrue(user.is_banned)
        response = self.client.post(
            reverse('unban_user', kwargs={'user_uuid': user.uuid}),
            {'user': user.pk, 'confirm': 1}
        )
        self.assertRedirects(
            response, reverse('user_details', kwargs={'user_uuid': user.uuid}))
        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.is_banned)

    def test_form_valid_not_confirmed(self):
        """Test that a user is not banned when confirm=False"""
        user = mommy.make('accounts.User', is_banned=True)
        self.assertTrue(user.is_banned)
        response = self.client.post(
            reverse('unban_user', kwargs={'user_uuid': user.uuid}),
            {'user': user.pk}
        )
        self.assertRedirects(
            response, reverse('user_details', kwargs={'user_uuid': user.uuid}))
        user = User.objects.get(pk=user.pk)
        self.assertTrue(user.is_banned)


class BecomeUserViewTest(ConnectMessageTestCase):
    """Tests for the BecomeUserView."""
    def test_get_success_url(self):
        """Test get_success_url redirects to the right place."""
        view = views.BecomeUserView()
        view.request = self.request_factory.get('/')
        self.assertEqual(view.get_success_url(), reverse('threads'))

    def test_get_success_url_with_next(self):
        """Test get_success_url redirects to next if in the request GET."""
        view = views.BecomeUserView()
        view.request = self.request_factory.get('/?next=meow')
        self.assertEqual(view.get_success_url(), 'meow')

    def test_user_to_become(self):
        """Should return a user object corresponding to the user_uuid."""
        view = views.BecomeUserView()
        view.kwargs = {'user_uuid': self.normal_user.uuid}
        self.assertEqual(
            view.user_to_become,
            self.normal_user
        )

    def test_form_valid_updates_session(self):
        """form_valid should add impersonate_id to the session."""
        session = self.client.session
        self.assertNotIn('impersonate_id', session)
        self.client.post(
            reverse('become_user', kwargs={'user_uuid': self.normal_user.uuid}),
            {'user_to_become': self.normal_user.pk}
        )
        session = self.client.session
        self.assertEqual(session['impersonate_id'], self.normal_user.pk)

    def test_form_valid_does_not_update_session_without_permission(self):
        """form_valid should only update the session if user has permission."""
        client = Client()
        client.post(
            reverse('login'),
            {'username': 'staffuser@razzmatazz.local', 'password': 'moo'}
        )
        session = client.session
        self.assertNotIn('impersonate_id', session)
        client.post(
            reverse('become_user', kwargs={'user_uuid': self.normal_user.uuid}),
            {'user_to_become': self.normal_user.pk}
        )
        session = client.session
        self.assertNotIn('impersonate_id', session)

    def test_get_context_adds_user_to_become(self):
        """user_to_become should be added to the context."""
        response = self.client.get(
            reverse('become_user', kwargs={'user_uuid': self.normal_user.uuid}))
        self.assertEqual(response.context['user_to_become'], self.normal_user)


class UnbecomeUserTest(ConnectMessageTestCase):
    """Tests for unbecome_user view."""
    def test_unbecome_user(self):
        """View should remove impersonate_id from session and redirect."""
        session = self.client.session
        session['impersonate_id'] = self.normal_user.pk
        session.save()
        response = self.client.get(reverse('unbecome_user'))
        session = self.client.session
        self.assertNotIn('impersonate_id', session)
        self.assertRedirects(response, reverse('threads'))

    def test_unbecome_user_redirects_to_next(self):
        """If next is in GET, user should be redirected."""
        session = self.client.session
        session['impersonate_id'] = self.normal_user.pk
        session.save()
        user_profile = reverse(
            'user_details', kwargs={'user_uuid': self.normal_user.uuid})
        response = self.client.get(
            '%s?next=%s' % (reverse('unbecome_user'), user_profile))
        self.assertRedirects(response, user_profile)

    def test_unbecome_user_impersonate_id_not_in_session(self):
        """Fail silently if impersonate_id is not in the session."""
        session = self.client.session
        self.assertNotIn('impersonate_id', session)
        response = self.client.get(reverse('unbecome_user'))
        self.assertRedirects(response, reverse('threads'))


class TermsAndConductViewTest(ConnectTestMixin, TestCase):
    """Tests for accepting terms of service and code of conduct."""
    def test_user_accepted_terms_and_conduct(self):
        """Test that posting a valid form updates user and redirects."""
        user = self.create_user(tos_accepted_at=None, ucoc_accepted_at=None)
        self.assertIsNone(user.tos_accepted_at)
        self.assertIsNone(user.ucoc_accepted_at)
        self.client.login(username=user.email, password='moo')
        response = self.client.post(
            reverse('accept_terms_and_conduct'),
            {'accept_tos': True, 'accept_ucoc': True, 'next': '/?ok'}
        )
        # Target status code is 302 because / will redirect user to another page
        self.assertRedirects(response, '/?ok', target_status_code=302)
        user = User.objects.get(pk=user.pk)
        self.assertIsInstance(user.tos_accepted_at, datetime)
        self.assertIsInstance(user.ucoc_accepted_at, datetime)


class TutorialStatusViewTest(ConnectTestMixin, TestCase):
    """Tests for user_tutorial_view."""
    def setUp(self):
        """Setup the test"""
        self.request_factory = RequestFactory()

    def test_user_tutorial_view(self):
        """view should change the user's status and
            return the expected response."""
        request = self.request_factory.post('/')
        user = self.create_user()
        request.user = user

        self.assertEqual(user.has_viewed_tutorial, False)
        views.user_tutorial_view(request)
        self.assertEqual(user.has_viewed_tutorial, True)
        views.user_tutorial_view(request)
        self.assertEqual(user.has_viewed_tutorial, False)
