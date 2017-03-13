"""Tests for group models."""
# pylint: disable=invalid-name, maybe-no-member
from datetime import datetime
from decimal import Decimal
from json import loads
from unittest import skipIf, TestCase
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files import File
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseNotAllowed, HttpResponseNotFound
from django.test import Client, RequestFactory
from django.test import TestCase as DjangoTestCase
from mock import patch, call, Mock
from model_mommy import mommy

# accounts.models isn't used but needs to be loaded for UserAutocomplete to be
# registered.
# pylint: disable=unused-import
from open_connect.accounts import models
from open_connect.groups import views
from open_connect.groups.forms import GroupInviteForm
from open_connect.groups.models import Group, GroupRequest
from open_connect.groups.views import GroupUpdateView
from open_connect.media.models import Image
from open_connect.notifications.forms import SubscriptionForm
from open_connect.connectmessages.models import Thread
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import ConnectTestMixin


USER_MODEL = get_user_model()
IS_SQLITE = settings.DATABASES['default']['ENGINE'].endswith('sqlite3')


def get_group_permission(codename):
    """Helper to get a specific group permission"""
    return Permission.objects.get(
        content_type__app_label='groups', codename=codename)


class GroupCreateViewTest(ConnectTestMixin, DjangoTestCase):
    """Tests for GroupCreateView"""
    def setUp(self):
        """Setup the GroupCreateViewTest TestCase"""
        self.user = self.create_superuser()
        self.client.login(username=self.user.email, password='moo')

    def test_add_group_permission_required(self):
        """User without add_group permission should get a 403."""
        user = self.create_user()
        c = Client()
        c.login(username=user.email, password='moo')
        response = c.get(reverse('create_group'))
        self.assertEqual(response.status_code, 403)

    def test_redirects_to_details_on_success(self):
        """User with permission posting a valid form should be redirected."""
        response = self.client.post(
            reverse('create_group'),
            {
                'authgroup_form-name': 'Writing tests on a Friday',
                'group_form-category': '1'}
        )
        group = Group.objects.latest('pk')
        self.assertRedirects(
            response,
            reverse('group_details', args=[group.pk])
        )

    def test_prefix_in_form_kwargs(self):
        """Forms in view should be prefixed."""
        response = self.client.get(reverse('create_group'))
        self.assertEqual(
            response.context_data['authgroup_form'].prefix, 'authgroup_form')
        self.assertEqual(
            response.context_data['group_form'].prefix, 'group_form')

    def test_form_valid_creates_authgroup_and_group(self):
        """A valid post should create a new group and authgroup."""
        response = self.client.post(
            reverse('create_group'),
            {
                'authgroup_form-name': 'Writing tests on a Friday',
                'group_form-category': '1',
                'group_form-description': 'This is a new group.'}
        )
        self.assertEqual(response.status_code, 302)
        group = Group.objects.latest('pk')
        self.assertEqual(group.group.name, 'Writing tests on a Friday')
        self.assertEqual(group.description, 'This is a new group.')

    def test_form_valid_saves_image(self):
        """A valid post with an image should store the image."""
        path = os.path.dirname(os.path.abspath(__file__))
        small_image = os.path.join(path, '200x200.gif')
        with open(small_image) as fp:
            self.client.post(
                reverse('create_group'),
                {
                    'authgroup_form-name': 'Writing tests on a Friday',
                    'group_form-category': '1',
                    'image_form-image': fp}
            )

        group = Group.objects.latest('pk')
        self.assertIsNotNone(group.image)

    def test_form_valid_no_image(self):
        """If no image is posted, the group image should be None."""
        self.client.post(
            reverse('create_group'),
            {
                'authgroup_form-name': 'Writing tests on a Friday',
                'group_form-category': '1'}
        )

        group = Group.objects.latest('pk')
        self.assertIsNone(group.image)

    def test_user_added_to_group(self):
        """User should be added as a member and an owner of the group."""
        self.client.post(
            reverse('create_group'),
            {
                'authgroup_form-name': 'Writing tests on a Friday',
                'group_form-category': '1'}
        )

        group = Group.objects.latest('pk')
        self.assertTrue(group.owners.filter(pk=self.user.pk).exists())
        self.assertTrue(self.user.groups_joined.filter(pk=group.pk).exists())

    def test_created_by_is_current_user(self):
        """created_by should be set to the currently authenticated user."""
        self.client.post(
            reverse('create_group'),
            {
                'authgroup_form-name': 'Writing tests on a Friday',
                'group_form-category': '1'}
        )

        group = Group.objects.latest('pk')
        self.assertEqual(group.created_by, self.user)


class GroupUpdateViewTest(ConnectTestMixin, DjangoTestCase):
    """Tests for GroupUpdateView."""
    def setUp(self):
        """Setup the GroupUpdateViewTest TestCase"""
        self.group = self.create_group()

    def test_regular_users_get_404(self):
        """Test that regular users cannot view nor edit"""
        group = self.create_group(
            group__name='Original Name', description='First Description')

        user = self.create_user()
        self.login(user)

        get_response = self.client.get(reverse('update_group', args=[group.pk]))
        self.assertEqual(get_response.status_code, 404)

        post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'New Name',
                'group_form-description': 'Second Description'
            })
        self.assertEqual(post_response.status_code, 404)

        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.group.name, 'Original Name')
        self.assertEqual(updated_group.description, 'First Description')

    def test_edit_any_group_can_edit(self):
        """A users with the can_edit_any_group permission can update group"""
        group = self.create_group(
            group__name='Original Name', description='First Description')

        user = self.create_user()
        edit_any_group_permission = get_group_permission('can_edit_any_group')
        user.user_permissions.add(edit_any_group_permission)
        self.login(user)

        post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'New Name',
                'group_form-description': 'Second Description'
            })
        self.assertEqual(post_response.status_code, 302)

        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.group.name, 'New Name')
        self.assertEqual(updated_group.description, 'Second Description')

    def test_group_owners_can_edit(self):
        """Group owners can edit their own group"""
        group = self.create_group(
            group__name='Original Name', description='First Description')

        user = self.create_user()
        group.owners.add(user)
        self.login(user)

        post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'New Name',
                'group_form-description': 'Second Description'
            })
        self.assertEqual(post_response.status_code, 302)

        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.group.name, 'New Name')
        self.assertEqual(updated_group.description, 'Second Description')

    def test_edit_featured_restriction(self):
        """Group owners should not be able to update featured status"""
        group = self.create_group(featured=False)

        user = self.create_user()
        group.owners.add(user)
        self.login(user)

        post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'New Name',
                'group_form-featured': '1'
            })
        self.assertEqual(post_response.status_code, 302)

        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.group.name, 'New Name')
        self.assertEqual(updated_group.featured, False)

    def test_caregory_change_restriction(self):
        """Group owners shouldn't change category without permission"""
        # Create 2 categories and a group
        old_category = mommy.make('groups.Category')
        new_category = mommy.make('groups.Category')
        group = self.create_group(
            category=old_category, group__name='Old Name')

        # Create a user for this test. Make that user an owner of the group
        # then log that user into the test client
        user = self.create_user()
        group.owners.add(user)
        self.login(user)

        # Send a POST request with enough information to change the category
        post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'New Name',
                'group_form-category': new_category.pk
            })
        # Confirm the POST was successful, as successful POSTs redirect
        self.assertEqual(post_response.status_code, 302)

        # Refresh the group from the database and make sure the name is
        # correct but the old category persisted
        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.group.name, 'New Name')
        self.assertEqual(updated_group.category, old_category)

        # Add the permission
        change_category_permission = get_group_permission(
            'can_edit_group_category')
        user.user_permissions.add(change_category_permission)

        # We need to re-add the user to the group owners, since the previous
        # POST request cleared out our owners
        group.owners.add(user)

        second_post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'New Name',
                'group_form-category': new_category.pk
            })
        self.assertEqual(second_post_response.status_code, 302)

        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.category, new_category)

    def test_featured_change_restrictions(self):
        """Group owners shouldn't change featured status without permission"""
        group = self.create_group(featured=False, group__name='Old Name')
        user = self.create_user()
        group.owners.add(user)

        self.login(user)

        # Send a POST request with enough information to change the featured
        # status
        post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'New Name',
                'group_form-featured': '1'
            })
        # Confirm the POST was successful, as successful POSTs redirect
        self.assertEqual(post_response.status_code, 302)

        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.group.name, 'New Name')
        self.assertFalse(updated_group.featured)

        # Add the permission
        change_category_permission = get_group_permission(
            'can_edit_group_featured')
        user.user_permissions.add(change_category_permission)

        # We need to re-add the user to the group owners, as the previous
        # POST cleared out our owners
        group.owners.add(user)

        # Send a POST request with enough information to change the featured
        # status
        post_response = self.client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'Second Name',
                'group_form-featured': '1'
            })
        # Confirm the POST was successful, as successful POSTs redirect
        self.assertEqual(post_response.status_code, 302)

        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.group.name, 'Second Name')
        self.assertTrue(updated_group.featured)

    def test_superuser_can_update_group(self):
        """Superusers should be able to update any group."""
        self.assertNotEqual(self.group.group.name, 'TGIF')
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        response = self.client.post(
            reverse('update_group', args=[self.group.pk]),
            {
                'authgroup_form-name': 'TGIF',
                'group_form-category': '1'}
        )
        self.assertRedirects(
            response, reverse('group_details', args=[self.group.pk]))
        group = Group.objects.get(pk=self.group.pk)
        self.assertEqual(group.group.name, 'TGIF')

    def test_user_with_edit_all_perm_can_update_group(self):
        """Users with can_edit_any_group perm should be able to update."""
        group = self.create_group()
        user = self.create_user()
        permission = Permission.objects.get(codename='can_edit_any_group')
        user.user_permissions.add(permission)
        client = Client()
        client.login(username=user.email, password='moo')
        response = client.post(
            reverse('update_group', args=[group.pk]),
            {
                'authgroup_form-name': 'TGIF',
                'group_form-category': '1'}
        )
        self.assertRedirects(
            response, reverse('group_details', args=[group.pk]))
        group = Group.objects.get(pk=group.pk)
        self.assertEqual(group.group.name, 'TGIF')

    def test_group_property(self):
        """Group.group property returns the group object."""
        group_update_view = GroupUpdateView()
        # Django would set this normally, but we're not testing the view here,
        # just testing the method works as intended given everything else works.
        group_update_view.kwargs = {'pk': self.group.pk}
        self.assertEqual(group_update_view.group, self.group)

    def test_group_property_doesnt_update_if_already_set(self):
        """Group.group property only looks up the group if it's unset."""
        # pylint: disable=protected-access
        group_update_view = GroupUpdateView()
        group_update_view._group = 'salooooooon!'
        self.assertEqual(group_update_view.group, 'salooooooon!')

    def test_group_added_to_context(self):
        """The group object should be in the context"""
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('update_group', args=[self.group.pk]))
        self.assertEqual(response.context_data['group'], self.group)

    def test_user_not_added_to_group(self):
        """The user should not be added as a group owner or member on update."""
        user = self.create_superuser()
        c = Client()
        c.login(username=user.email, password='moo')
        c.post(
            reverse('update_group', args=[self.group.pk]),
            {
                'authgroup_form-name': 'Whatever',
                'group_form-category': '1'}
        )

        self.assertFalse(self.group.owners.filter(pk=user.pk).exists())
        self.assertFalse(user.groups_joined.filter(pk=self.group.pk).exists())

    def test_created_by_is_not_updated(self):
        """created_by should not be changed when updating a group."""
        user = self.create_superuser()
        client = Client()
        client.login(username=user.email, password='moo')
        client.post(
            reverse('create_group'),
            {
                'authgroup_form-name': 'Writing tests on a Friday',
                'group_form-category': '1'}
        )

        group = Group.objects.latest('pk')
        self.assertEqual(group.created_by, user)


class GroupListViewTest(ConnectMessageTestCase, ConnectTestMixin):
    """Tests for GroupListView."""
    def setUp(self):
        """Setup the test"""
        # Call the super() method for setUp
        super(GroupListViewTest, self).setUp()

        # pylint: disable=no-value-for-parameter
        self.view = views.GroupListView.as_view()

        # Create a new django client which is not logged in
        self.anonymous_client = Client()

    @skipIf(IS_SQLITE, "Test not supported when using sqlite backend.")
    @patch.object(views, 'get_coordinates')
    def test_location_provided(self, mock_get_coordinates):
        """Should call get_coordinates"""
        mock_get_coordinates.return_value = 1, 1
        self.assertEqual(mock_get_coordinates.call_count, 0)
        request = self.request_factory.get('/?location=60657')
        request.user = self.user1
        self.view(request)
        self.assertEqual(mock_get_coordinates.call_count, 1)

    @patch.object(views.Group.objects, 'search')
    def test_coords_and_query(self, mock_search):
        """Location and search are passed when in request query string."""
        self.assertEqual(mock_search.call_count, 0)
        request = self.request_factory.get('/?location=1,1&q=something')
        request.user = self.user1
        self.view(request)
        self.assertEqual(
            mock_search.call_args,
            call(
                search=u'something',
                location=(Decimal('1'), Decimal('1'))
            )
        )
        self.assertEqual(mock_search.call_count, 1)

    @patch.object(views.Group.objects, 'search')
    def test_coords_no_query(self, mock_search):
        """Only location is passed when location is in querystring."""
        self.assertEqual(mock_search.call_count, 0)
        request = self.request_factory.get('/?location=1,1')
        request.user = self.user1
        self.view(request)
        self.assertEqual(
            mock_search.call_args,
            call(search=None, location=(Decimal('1'), Decimal('1')))
        )
        self.assertEqual(mock_search.call_count, 1)

    @patch.object(views.Group.objects, 'search')
    def test_query_no_coords(self, mock_search):
        """Only search is passed when search is in querystring."""
        self.assertEqual(mock_search.call_count, 0)
        request = self.request_factory.get('/?q=something')
        request.user = self.user1
        self.view(request)
        self.assertEqual(
            mock_search.call_args,
            call(search=u'something', location=None)
        )
        self.assertEqual(mock_search.call_count, 1)

    @patch.object(views.Group.objects, 'published')
    def test_noloc_calls_published(self, mock_published):
        """If noloc is in query string, look up all published groups."""
        self.assertEqual(mock_published.call_count, 0)
        request = self.request_factory.get('/?noloc')
        request.user = self.user1
        self.view(request)
        self.assertEqual(mock_published.call_count, 1)

    def test_anonymous_visitor_no_login(self):
        """Confirm that anonymous visitors are not sent to a login page"""
        # The /explore/ path is the path that is login-exempt. This is usually
        # set in the urls.py for the overall site
        response = self.anonymous_client.get(reverse('explore'))

        # Confirm that the page returned with a 200 status code, instead of
        # sending the user to a login page
        self.assertEqual(response.status_code, 200)

    def test_anonymous_visitor_group_view_permission(self):
        """Test an anonymous visitor sees only public groups"""
        public_group = self.create_group(published=True)
        private_group = self.create_group(published=False)

        # The /explore/ path is the path that is login-exempt. This is usually
        # set in the urls.py for the overall site
        response = self.anonymous_client.get(reverse('explore'))

        # Confirm that the page returned with a 200 status code
        self.assertEqual(response.status_code, 200)

        # Confirm that the public group is listed
        self.assertContains(response, public_group.group.name)

        # Confirm that the private group is not requested
        self.assertNotContains(response, private_group.group.name)


class HandleGroupSubscriptionTest(ConnectMessageTestCase):
    """Tests for handle_group_subscription view."""
    def test_group_id_not_in_request(self):
        """Correct error returned when group_id isn't in request."""
        response = views.handle_group_subscription(self.request, 'subscribe')
        content = loads(response.content)
        self.assertFalse(content['success'])
        self.assertEqual(content['message'], "Requested group doesn't exist.")
        self.assertEqual(content['group_id'], -1)

    def test_group_does_not_exist(self):
        """Correct error is returned when group_id doesn't match a group."""
        self.assertFalse(Group.objects.filter(pk=99999).exists())
        request = self.request_factory.post('/', {'group_id': 99999})
        request.user = self.user1
        response = views.handle_group_subscription(request, 'subscribe')
        content = loads(response.content)
        self.assertFalse(content['success'])
        self.assertEqual(content['message'], "Requested group doesn't exist.")
        self.assertEqual(content['group_id'], '99999')

    def test_subscribe_to_private_group(self):
        """Correct response when requesting membership to a private group."""
        private_group = Group.objects.create(name='Private group', private=True)
        request = self.request_factory.post('/', {'group_id': private_group.pk})
        request.user = self.user1
        response = views.handle_group_subscription(request, 'subscribe')
        content = loads(response.content)
        self.assertTrue(content['success'])
        self.assertEqual(
            content['message'],
            'Your request to join Private group has been received.'
        )
        self.assertEqual(content['group_id'], private_group.pk)

    def test_subscribe_to_non_private_group(self):
        """Correct response when joining a non-private group."""
        request = self.request_factory.post('/', {'group_id': self.group.pk})
        request.user = self.user1
        response = views.handle_group_subscription(request, 'subscribe')
        content = loads(response.content)
        self.assertTrue(content['success'])
        self.assertEqual(
            content['message'],
            '<div>Successfully joined %s.</div>' % self.group.group.name
        )
        self.assertEqual(content['group_id'], self.group.pk)

    def test_unsubscribe(self):
        """Correct response when unsubscribing from a group."""
        self.user1.add_to_group(self.group.pk)
        request = self.request_factory.post('/', {'group_id': self.group.pk})
        request.user = self.user1
        response = views.handle_group_subscription(request, 'unsubscribe')
        content = loads(response.content)
        self.assertTrue(content['success'])
        self.assertEqual(
            content['message'],
            'Successfully unsubscribed from %s.' % self.group.group.name
        )
        self.assertEqual(content['group_id'], self.group.pk)


class GroupRequestUpdateViewTest(ConnectMessageTestCase):
    """Tests for GroupRequestUpdateView."""
    def test_only_show_groups_user_is_owner_of(self):
        """Only requests for groups the user owns should be displayed."""
        # pylint: disable=no-value-for-parameter
        self.group.owners.add(self.staff_user)
        self.group.private = True
        self.group.save()
        group2 = Group.objects.create(name='Second group')
        group_request_one = GroupRequest.objects.create(
            user=self.user2, group=self.group)
        group_request_two = GroupRequest.objects.create(
            user=self.user2, group=group2)
        group_request_update_view = views.GroupRequestUpdateView.as_view()
        request = self.request_factory.get('/')
        request.user = self.staff_user
        response = group_request_update_view(request)
        context = response.context_data
        self.assertEqual(context['request_count'], 1)
        open_requests = context['form'].fields['open_requests'].queryset
        self.assertIn(group_request_one, open_requests)
        self.assertNotIn(group_request_two, open_requests)

    def test_superuser_sees_all_group_requests(self):
        """Superusers should see all open requests."""
        # pylint: disable=no-value-for-parameter
        self.group.owners.add(self.staff_user)
        self.group.private = True
        self.group.save()
        group2 = Group.objects.create(name='Second group')
        group_request_one = GroupRequest.objects.create(
            user=self.user2, group=self.group)
        group_request_two = GroupRequest.objects.create(
            user=self.user2, group=group2)
        group_request_update_view = views.GroupRequestUpdateView.as_view()
        response = group_request_update_view(self.request)
        context = response.context_data
        self.assertEqual(context['request_count'], 2)
        open_requests = context['form'].fields['open_requests'].queryset
        self.assertIn(group_request_one, open_requests)
        self.assertIn(group_request_two, open_requests)

    def test_redirects_to_moderate__group_requests_on_success(self):
        """Successful moderation should redirect user back to the same page."""
        group_request_one = GroupRequest.objects.create(
            user=self.user2, group=self.group)
        response = self.client.post(
            reverse('moderate_requests'),
            {'open_requests': group_request_one.pk, 'action': 'approve'}
        )
        self.assertRedirects(response, reverse('moderate_requests'))
        group_request_one = GroupRequest.objects.get(pk=group_request_one.pk)
        self.assertTrue(group_request_one.approved)


class GroupImagesViewTest(ConnectTestMixin, ConnectMessageTestCase):
    """Tests for GroupImagesView."""
    def setUp(self):
        """Setup the GroupImagesViewTest TestCase"""
        super(GroupImagesViewTest, self).setUp()
        path = os.path.dirname(os.path.abspath(__file__))
        self.smallfile = path + '/200x200.gif'

        self.message1img = Image()
        self.message1img.user = self.message1.sender
        self.message1img.image = File(open(self.smallfile))
        self.message1img.save()
        self.message1.images.add(self.message1img)

        self.message3img = Image()
        self.message3img.user = self.message3.sender
        self.message3img.image = File(open(self.smallfile))
        self.message3img.save()
        self.message3.images.add(self.message3img)

        self.client2 = Client()
        self.client2.post(
            reverse('login'),
            {
                'username': 'gracegrant@razzmatazz.local',
                'password': 'moo'
            })

    def request_multiple_users(self, group):
        """Requests group images as two different users."""
        user1_response = self.client.get(
            reverse('group_images', kwargs={'group_id': group.pk}))
        user2_response = self.client2.get(
            reverse('group_images', kwargs={'group_id': group.pk}))
        return user1_response, user2_response

    def test_only_images_posted_to_group_available(self):
        """Only images posted to a group should be in the group gallery."""
        response = self.client.get(
            reverse('group_images', kwargs={'group_id': self.group1.pk}))
        self.assertContains(response, self.message1img.get_thumbnail)
        self.assertContains(
            response,
            reverse('image', kwargs={'image_uuid': self.message1img.uuid})
        )
        self.assertNotContains(response, self.message3img.get_thumbnail)
        self.assertNotContains(
            response,
            reverse('image', kwargs={'image_uuid': self.message3img.uuid})
        )

    def test_moderated_messages_properly_appear(self):
        """
        Test that messages appear differently to different users
        depending on the message's moderation status
        """

        # Create a new group
        group = mommy.make(Group)
        self.user1.add_to_group(group.pk)
        self.user2.add_to_group(group.pk)

        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=group)
        message = mommy.make(
            'connectmessages.Message', thread=thread, sender=self.user1)

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        # Test the visibility of an image when the message has not yet been
        # approved by a group moderator
        message.status = 'pending'
        message.save()
        sender_response, receiver_response = self.request_multiple_users(group)
        self.assertContains(sender_response, image1.get_thumbnail)
        self.assertNotContains(receiver_response, image1.get_thumbnail)

        # Test the visibility when the message has been approved
        message.status = 'approved'
        message.save()
        sender_response, receiver_response = self.request_multiple_users(group)
        self.assertContains(sender_response, image1.get_thumbnail)
        self.assertContains(receiver_response, image1.get_thumbnail)

        # As we want spammers to think their content was approved, test when
        # a message has been marked as spam
        message.status = 'spam'
        message.save()
        sender_response, receiver_response = self.request_multiple_users(group)
        self.assertContains(sender_response, image1.get_thumbnail)
        self.assertNotContains(receiver_response, image1.get_thumbnail)

    def test_no_images_from_banned_users(self):
        """Test that images posted by banned users are not visible."""
        banned_user = mommy.make('accounts.User', is_banned=True)
        group = mommy.make(Group)
        banned_user.add_to_group(group.pk)
        self.user2.add_to_group(group.pk)

        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=group)
        message = mommy.make(
            'connectmessages.Message', thread=thread, sender=banned_user)

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        result = self.client.get(
            reverse('group_images', kwargs={'group_id': group.pk}))
        self.assertNotIn(image1, result.context['images'])

    def test_images_from_a_banned_user_are_visible_to_banned_user(self):
        """Images posted by banned members are visible to the banned member."""
        banned_user = self.create_user(is_banned=True)
        group = mommy.make(Group)
        banned_user.add_to_group(group.pk)
        self.user2.add_to_group(group.pk)

        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=group)
        message = mommy.make(
            'connectmessages.Message', thread=thread, sender=banned_user)

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        client = Client()
        client.post(
            reverse('login'),
            {'username': banned_user.email, 'password': 'moo'}
        )
        result = client.get(
            reverse('group_images', kwargs={'group_id': group.pk}))
        self.assertIn(image1, result.context['images'])


class GroupDetailViewTest(ConnectTestMixin, DjangoTestCase):
    """Tests for the GroupDetailView."""
    def test_only_public_threads_visible(self):
        """Only public threads should be visible on the group detail page."""
        # Create a new thread and message
        user = self.create_user()
        group = self.create_group()
        user.add_to_group(group.pk)
        public_thread = self.create_thread(group=group, sender=user)
        private_thread = self.create_thread(
            group=group, visible=False, sender=user)

        self.login(user)
        response = self.client.get(
            reverse('group_details', kwargs={'pk': group.pk}))

        self.assertIn(public_thread, response.context['public_threads'])
        self.assertNotIn(private_thread, response.context['public_threads'])

    def test_subscription_form_added_to_context(self):
        """SubscriptionForm should be in view context if user is subscribed."""
        user = self.create_user()
        group = self.create_group()
        user.add_to_group(group.pk)

        self.login(user)
        response = self.client.get(
            reverse('group_details', kwargs={'pk': group.pk}))

        self.assertIsInstance(
            response.context['subscription_form'], SubscriptionForm)

    def test_subscription_form_user_is_not_subscribed(self):
        """No SubscriptionForm in context if user is not subscribed."""
        user = self.create_user()
        group = self.create_group()

        self.login(user)
        response = self.client.get(
            reverse('group_details', kwargs={'pk': group.pk}))

        self.assertIsNone(response.context['subscription_form'])

    def test_threads_ordered_by_most_recently_active(self):
        """The three threads shown should be most recently active threads."""
        sender = self.create_user()
        group = self.create_group()
        sender.add_to_group(group.pk)

        thread1 = self.create_thread(sender=sender, group=group)
        thread1.first_message.created_at = datetime(2014, 10, 31, 1, 0, 0)
        thread1.first_message.save()

        thread2 = self.create_thread(sender=sender, group=group)
        thread2.first_message.created_at = datetime(2014, 10, 31, 2, 0, 0)
        thread2.first_message.save()

        thread3 = self.create_thread(sender=sender, group=group)
        thread3.first_message.created_at = datetime(2014, 10, 31, 3, 0, 0)
        thread3.first_message.save()

        thread4 = self.create_thread(sender=sender, group=group)
        thread4.first_message.created_at = datetime(2014, 10, 31, 4, 0, 0)
        thread4.first_message.save()

        self.login(sender)
        response = self.client.get(
            reverse('group_details', kwargs={'pk': group.pk}))

        # At this point thread1 should be out.
        self.assertQuerysetItemsEqual(
            response.context['public_threads'],
            Thread.objects.filter(pk__in=[thread2.pk, thread3.pk, thread4.pk])
        )

        # Add a new message to thread1.
        message = mommy.make(
            'connectmessages.Message',
            thread=thread1,
            sender=sender,
        )
        message.created_at = datetime(2014, 10, 31, 5, 0, 0)
        message.save()

        response = self.client.get(
            reverse('group_details', kwargs={'pk': group.pk}))

        # Now that thread1 is most recently active, it should be on the page.
        self.assertQuerysetItemsEqual(
            response.context['public_threads'],
            Thread.objects.filter(pk__in=[thread1.pk, thread3.pk, thread4.pk])
        )


class GroupMemberListViewTest(ConnectTestMixin, DjangoTestCase):
    """Tests for GroupMemberListView."""
    def test_member_list_published(self):
        """Test that a member of a group is on a published member list."""
        member = self.create_user()
        group = mommy.make('groups.Group', member_list_published=True)
        member.add_to_group(group.pk)

        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk})
        )
        self.assertIn(member, response.context['group_members'])

    def test_member_list_is_not_published(self):
        """Test that member list returns 404 if not published."""
        group = mommy.make('groups.Group', member_list_published=False)
        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk}))
        self.assertIsInstance(response, HttpResponseNotFound)

    def test_member_list_is_not_published_user_is_su(self):
        """Member list should always be visible to superusers."""
        member = self.create_user()
        group = mommy.make('groups.Group', member_list_published=False)
        member.add_to_group(group.pk)

        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk})
        )
        self.assertIn(member, response.context['group_members'])

    def test_member_list_is_not_published_user_is_owner(self):
        """Member list should always be visible to group owners."""
        member = self.create_user()
        group = mommy.make('groups.Group', member_list_published=False)
        member.add_to_group(group.pk)

        user = self.create_user()
        group.owners.add(user)
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk})
        )
        self.assertIn(member, response.context['group_members'])

    def test_with_query(self):
        """Query should filter the list of members."""
        member1 = self.create_user(first_name='Doctor Pepper')
        member2 = self.create_user()
        group = mommy.make('groups.Group')
        member1.add_to_group(group.pk)
        member2.add_to_group(group.pk)

        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk}),
            {'q': 'Doctor'}
        )
        self.assertIn(member1, response.context['group_members'])
        self.assertNotIn(member2, response.context['group_members'])

    def test_user_is_owner(self):
        """user_is_owner should be True."""
        user = self.create_user()
        group = mommy.make('groups.Group')
        group.owners.add(user)
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk})
        )
        self.assertTrue(response.context['user_is_owner'])

    def test_user_is_not_owner(self):
        """user_is_owner should be False."""
        user = self.create_user()
        group = mommy.make('groups.Group')
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk})
        )
        self.assertFalse(response.context['user_is_owner'])

    def test_group_members_excludes_owners(self):
        """The group_members context var should exclude owners."""
        group = mommy.make('groups.Group')
        owner = self.create_user()
        owner.add_to_group(group.pk)
        group.owners.add(owner)
        member = self.create_user()
        member.add_to_group(group.pk)

        user = self.create_user()
        self.login(user)
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk}))

        self.assertIn(member, response.context['group_members'])
        self.assertNotIn(owner, response.context['group_members'])

    def test_group_owners_is_only_owners(self):
        """The group_owners context var should exclude normal members."""
        group = mommy.make('groups.Group')
        owner = self.create_user()
        owner.add_to_group(group.pk)
        group.owners.add(owner)
        member = self.create_user()
        member.add_to_group(group.pk)

        user = self.create_user()
        self.login(user)
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk}))

        self.assertIn(owner, response.context['group_owners'])
        self.assertNotIn(member, response.context['group_owners'])

    def test_group_member_count(self):
        """Test that the context contains the total number of members"""
        group = self.create_group()
        member1 = self.create_user()
        member2 = self.create_user()
        member3 = self.create_user()

        member1.add_to_group(group.pk)
        member2.add_to_group(group.pk)
        member3.add_to_group(group.pk)

        self.login(member1)
        response = self.client.get(
            reverse('group_members', kwargs={'pk': group.pk}))

        self.assertEqual(3, response.context['total_members'])


class TestQuickAddUserToGroup(ConnectMessageTestCase):
    """Tests for group_quick_user_add."""
    @patch('open_connect.groups.views.add_user_to_group')
    def test_successful_addition(self, mock):
        """Test a successful addition of 2 users to a group"""
        group = mommy.make(Group)
        result = self.client.post(
            reverse(
                'group_quick_user_add',
                args=[group.pk]),
            {'users': [self.user1.pk, self.user2.pk]}
        )
        self.assertIn('2 Users Added', result.cookies['messages'].value)
        self.assertEqual(mock.delay.call_count, 2)

    @patch('open_connect.groups.views.render_to_string')
    def test_successful_addition_message(self, mock):
        """Test that the addition of a user creates a proper notification"""
        group = mommy.make(Group)
        result = self.client.post(
            reverse(
                'group_quick_user_add',
                args=[group.pk]),
            {'users': [self.user1.pk]}
        )
        self.assertIn('1 User Added', result.cookies['messages'].value)
        mock.assert_called_with(
            'groups/notifications/added_to_group_notification.html',
            {'group': group}
        )

    @patch('open_connect.groups.views.add_user_to_group')
    def test_blank_post(self, mock):
        """Test a submission with no users attached"""
        result = self.client.post(
            reverse(
                'group_quick_user_add',
                args=[self.group1.pk]),
            {'users': []}
        )
        self.assertIn('No Users Entered', result.cookies['messages'].value)
        self.assertFalse(mock.called)


class TestGroupInviteView(TestCase):
    """Tests for GroupMemberInviteView"""
    def setUp(self):
        """Setup GroupInviteView tests"""
        self.user1 = mommy.make('accounts.User')
        self.user2 = mommy.make('accounts.User')
        self.request_user = mommy.make('accounts.User')
        self.group1 = mommy.make('groups.Group')
        self.user1.add_to_group(self.group1.pk)
        self.user2.add_to_group(self.group1.pk)
        self.view = views.GroupMemberInviteView()
        self.view.kwargs = {'pk': self.group1.pk}
        request_factory = RequestFactory()
        self.view.request = request_factory.get('/')
        self.view.request.user = self.request_user

        self.email_list = [
            self.user1.email,
            self.user2.email,
            'test3@example.com',
            'Test User 4 <test4@example.com>'
        ]
        self.emails = ', '.join(self.email_list)

        djmessages_patcher = patch('open_connect.groups.views.messages')
        self.mockdjmessage = djmessages_patcher.start()
        self.addCleanup(djmessages_patcher.stop)

    def test_get_success_url(self):
        """Test the get_success_url method"""
        url = self.view.get_success_url()
        self.assertEqual(url, reverse('group_details', args=[self.group1.pk]))

    def test_non_existent_group_throws_404(self):
        """Test requesting a group that does not exist throws a 404"""
        view = views.GroupMemberInviteView()
        view.kwargs = {'pk': 500000}
        with self.assertRaises(Http404):
            view.get_context_data()

    def test_non_verified_form_submit(self):
        """Test a submit where the user has not confirmed their submission"""
        form = GroupInviteForm({
            'emails': self.emails,
            'verified': False
        })
        self.assertTrue(form.is_valid())
        result = self.view.form_valid(form)

        context = result.context_data
        self.assertEqual(context['group'], self.group1)
        self.assertItemsEqual(
            list(context['existing'].values_list('pk', flat=True)),
            [self.user1.pk, self.user2.pk])
        self.assertEqual(
            context['new'],
            set([u'test3@example.com', u'test4@example.com'])
        )
        self.assertTrue(context['verify'])

    def test_verified_form_submit(self):
        """Test a valid form submit that is confirmed"""
        form = Mock()
        form.cleaned_data = {
            'emails': self.emails,
            'verified': True,
        }

        result = self.view.form_valid(form)
        self.assertEqual(form.group_id, self.group1.pk)
        self.assertEqual(form.user_id, self.request_user.pk)
        self.assertTrue(form.save.call_count, 1)

        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, self.view.get_success_url())


class TestGroupDeleteView(ConnectTestMixin, DjangoTestCase):
    """Tests for GroupDeleteView."""
    def test_group_is_deleted(self):
        """Test when a user confirms they want to delete a group."""
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        group = Group.objects.create(name='delete me')
        response = self.client.post(
            reverse('delete_group', kwargs={'pk': group.pk}),
            {'are_you_sure': 'yes'}
        )
        self.assertRedirects(response, reverse('groups'))
        group = Group.objects.with_deleted().get(pk=group.pk)
        self.assertEqual(group.status, 'deleted')

    def test_group_is_not_deleted(self):
        """Test when a user does not confirm they want to delete a group."""
        user = self.create_superuser()
        self.client.login(username=user.email, password='moo')
        group = Group.objects.create(name='please do not delete me')
        response = self.client.post(
            reverse('delete_group', kwargs={'pk': group.pk}),
            {'are_you_sure': 'no'}
        )
        self.assertRedirects(
            response, reverse('group_details', kwargs={'pk': group.pk}))
        group = Group.objects.get(pk=group.pk)
        self.assertEqual(group.status, 'active')


class TestRemoveUserFromGroupView(ConnectTestMixin, DjangoTestCase):
    """Tests for remove_user_from_group_view."""
    def test_current_user_is_owner(self):
        """The view should work when the current user is an owner."""
        owner = self.create_user(is_staff=True)
        group = Group.objects.create(name='test')
        group.owners.add(owner)
        user = self.create_user()
        user.add_to_group(group.pk)
        self.client.login(username=owner.email, password='moo')
        response = self.client.post(
            reverse('remove_user_from_group',
                    kwargs={'group_id': group.pk, 'user_uuid': user.uuid})
        )
        json_response = loads(response.content)
        self.assertEqual(json_response['errors'], '')
        self.assertTrue(json_response['success'])

    def test_current_user_is_not_owner(self):
        """The view should not work when the current user is not an owner."""
        someone = self.create_user(is_staff=True)
        group = Group.objects.create(name='test')
        user = self.create_user()
        user.add_to_group(group.pk)
        self.client.login(username=someone.email, password='moo')
        response = self.client.post(
            reverse('remove_user_from_group',
                    kwargs={'group_id': group.pk, 'user_uuid': user.uuid})
        )
        json_response = loads(response.content)
        self.assertEqual(
            json_response['error'], u'User is not an owner of this group.')
        self.assertFalse(json_response['success'])

    def test_not_post(self):
        """View should only accept POST requests."""
        someone = self.create_user(is_staff=True)
        group = Group.objects.create(name='test')
        user = self.create_user()
        user.add_to_group(group.pk)
        self.client.login(username=someone.email, password='moo')
        response = self.client.get(
            reverse('remove_user_from_group',
                    kwargs={'group_id': group.pk, 'user_uuid': user.uuid})
        )
        self.assertIsInstance(response, HttpResponseNotAllowed)
