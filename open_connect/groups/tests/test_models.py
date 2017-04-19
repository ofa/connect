"""Tests for group models."""
# pylint: disable=invalid-name, no-self-use
from unittest import skipIf

from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.query import EmptyQuerySet
from django.test import TestCase
from django.utils.timezone import now
from mock import patch
from model_mommy import mommy

from open_connect.connect_core.utils.basetests import ConnectTestMixin
from open_connect.groups import models
from open_connect.groups.models import Category, Group, GroupRequest
from open_connect.media.models import ShortenedURL
from open_connect.media.tests import get_in_memory_image_instance


IS_SQLITE = settings.DATABASES['default']['ENGINE'].endswith('sqlite3')


class GroupManagerTest(ConnectTestMixin, TestCase):
    """Group manager tests."""
    def test_create_with_name(self):
        """Group.group.name should be the name passed to create."""
        group = Group.objects.create(name='Some group')
        self.assertEqual(group.group.name, 'Some group')

    def test_create_with_name_and_auth_group(self):
        """If both group and name are given, prefer group over name."""
        auth_group = AuthGroup.objects.create(name='Some group')
        group = Group.objects.create(group=auth_group, name='Blahhhh')
        self.assertEqual(group.group.name, 'Some group')

    def test_published_has_published_groups(self):
        """Published groups should be returned in manager published method."""
        group = Group.objects.create(name='Some group')
        self.assertIn(group, Group.objects.published())

    def test_published_no_unpublished_groups(self):
        """Unpublished groups should not be returned in manager published."""
        group = Group.objects.create(name='Some group', published=False)
        self.assertNotIn(group, Group.objects.published())

    def test_active_groups_in_result(self):
        """Groups with active status should be included in all."""
        group = Group.objects.create(name='Hello')
        self.assertIn(group, Group.objects.all())

    def test_deleted_groups_not_in_result(self):
        """Groups with deleted status """
        group = Group.objects.create(name='Delete me!')
        group.delete()
        self.assertNotIn(group, Group.objects.all())

    def test_with_deleted_includes_deleted(self):
        """Deleted groups should still be in with_deleted."""
        group = Group.objects.create(name='find meeeee', status='deleted')
        self.assertIn(group, Group.objects.with_deleted())


class GroupManagerSearchTest(ConnectTestMixin, TestCase):
    """Tests for the group search manager."""
    @classmethod
    def setUpClass(cls):
        """Only create these once."""
        cls.regular_group = Group.objects.create(
            name='Regular',
            description='This is a group for people who like cheese.',
            latitude=41.903123,
            longitude=-87.685318,
            radius=10
        )
        cls.regular_group.tags.add(
            'Cheddar is better', 'I like muenster', 'Parmesan is yummy')
        cls.unpublished_group = Group.objects.create(
            name='Unpublished',
            published=False)

        # As `slug` is unique in category we must delete all non-default
        # categories to ensure that our 2 slugs have not been created
        # elsewhere
        Category.objects.exclude(pk=1).delete()
        cls.gvp_category = mommy.make('groups.Category', slug='gvp')
        cls.lgbt_category = mommy.make('groups.Category', slug='lgbt')

        cls.gvp_group = Group.objects.create(
            name='GVP',
            category=cls.gvp_category,
            description="No more violence.",
            latitude=42.397934,
            longitude=-87.836380,
            radius=50,
            state='NY'
        )
        cls.gvp_group.tags.add('guns', 'violence')
        cls.lgbt_group = Group.objects.create(
            name='LGBT',
            category=cls.lgbt_category,
            description='Gay pride!',
            latitude=43.655267,
            longitude=-79.384460,
            radius=50,
            state='IL'
        )
        cls.lgbt_group.tags.add('lesbian', 'gay')

    @classmethod
    def tearDownClass(cls):
        """Delete groups that aren't needed anymore."""
        cls.regular_group.delete()
        cls.unpublished_group.delete()
        cls.gvp_group.delete()
        cls.lgbt_group.delete()

    def test_no_targeting_options(self):
        """If nothing is passed to search, it should equal published."""
        self.assertQuerysetEqual(
            Group.objects.search(),
            [repr(item) for item in Group.objects.published()],
            ordered=False
        )

    def test_search_matches_category(self):
        """Searching by a string matches a group's category."""
        gvp_groups = Group.objects.search('gvp')
        self.assertIn(self.gvp_group, gvp_groups)
        self.assertNotIn(self.lgbt_group, gvp_groups)
        self.assertNotIn(self.regular_group, gvp_groups)
        self.assertNotIn(self.unpublished_group, gvp_groups)

    def test_search_matches_name(self):
        """Searching by a string matches a group's name."""
        name_groups = Group.objects.search(search='LGB')
        self.assertIn(self.lgbt_group, name_groups)
        self.assertNotIn(self.regular_group, name_groups)
        self.assertNotIn(self.unpublished_group, name_groups)
        self.assertNotIn(self.gvp_group, name_groups)

    def test_search_matches_description(self):
        """Searching by a string matches a group's description."""
        groups = Group.objects.search(search='violence')
        self.assertIn(self.gvp_group, groups)
        self.assertNotIn(self.regular_group, groups)
        self.assertNotIn(self.unpublished_group, groups)
        self.assertNotIn(self.lgbt_group, groups)

    def test_search_matches_tags(self):
        """Searching by a string matches a group's tags."""
        groups = Group.objects.search(search='parmesan-is-yummy')
        self.assertIn(self.regular_group, groups)
        self.assertNotIn(self.gvp_group, groups)
        self.assertNotIn(self.unpublished_group, groups)
        self.assertNotIn(self.lgbt_group, groups)

    @skipIf(IS_SQLITE, "Test not supported when using sqlite backend.")
    def test_search_location_has_distances(self):
        """Searching by location matches groups that are close."""
        groups = Group.objects.search(location=60657)
        self.assertTrue(
            all((hasattr(group, 'distance') for group in groups)))

    @skipIf(IS_SQLITE, "Test not supported when using sqlite backend.")
    def test_coords_targeting(self):
        """Searching by coordinates matches groups that are close."""
        groups = Group.objects.location_search((43.603097, -79.592514))
        self.assertIn(self.lgbt_group, groups)
        self.assertNotIn(self.regular_group, groups)
        self.assertNotIn(self.unpublished_group, groups)
        self.assertNotIn(self.gvp_group, groups)

    @skipIf(IS_SQLITE, "Test not supported when using sqlite backend.")
    def test_coords_string_targeting(self):
        """Searching by coordinates in a string matches close groups."""
        groups = Group.objects.location_search('43.603097, -79.592514')
        self.assertIn(self.lgbt_group, groups)
        self.assertNotIn(self.regular_group, groups)
        self.assertNotIn(self.unpublished_group, groups)
        self.assertNotIn(self.gvp_group, groups)

    @patch('open_connect.groups.models.get_coordinates')
    def test_coords_no_targets(self, mock):
        """If no coordinates are returned return an empty QuerySet"""
        mock.return_value = None

        groups = Group.objects.location_search('None, None')

        mock.assert_called_once_with('None, None')

        self.assertIsInstance(groups, EmptyQuerySet)


class GroupTest(ConnectTestMixin, TestCase):
    """Test group methods."""
    def test_unicode(self):
        """Unicode conversion returns unicode of the group's name."""
        group = Group.objects.create(name='Some group')
        self.assertEqual(unicode(group), u'Some group')

    def test_get_absolute_url(self):
        """Test getting the absolute URL of a group"""
        group = mommy.make(Group)
        url = group.get_absolute_url()
        self.assertEqual(url, reverse(
            'group_details', args=(group.pk,)))

    def test_full_url(self):
        """Unicode conversion returns unicode of the group's name."""
        group = mommy.make(Group)
        url = group.full_url
        self.assertEqual(url, settings.ORIGIN + reverse(
            'group_details', args=(group.pk,)))
        self.assertIn('http', url)
        self.assertIn(str(group.pk), url)

    def test_clean_location_fields(self):
        """Clean should run without errors with coordinates and radius."""
        group = Group.objects.create(
            name='Some group',
            latitude='123',
            longitude='123',
            radius='10'
        )
        self.assertIsNone(group.clean())

    def test_clean_location_fields_latitude_missing(self):
        """Clean raises ValidationError if latitude is missing."""
        group = Group.objects.create(
            name='Some group',
            longitude='123',
            radius='10'
        )
        self.assertRaises(ValidationError, group.clean)

    def test_clean_location_fields_longitude_missing(self):
        """Clean raises ValidationError if longitude is missing."""
        group = Group.objects.create(
            name='Some group',
            latitude='123',
            radius='10'
        )
        self.assertRaises(ValidationError, group.clean)

    def test_clean_location_fields_radius_missing(self):
        """Clean raises ValidationError if radius is missing."""
        group = Group.objects.create(
            name='Some group',
            latitude='123',
            longitude='123',
        )
        self.assertRaises(ValidationError, group.clean)

    def test_clean_location_fields_no_location_fields(self):
        """Clean runs without errors if no location data is set."""
        group = Group.objects.create(name='Some group')
        self.assertIsNone(group.clean())

    def test_get_members(self):
        """Group.get_members() returns users that are in a group."""
        group = mommy.make(Group)
        user = self.create_user()
        user.add_to_group(group.pk)
        self.assertIn(user, group.get_members())

        user.remove_from_group(group)
        self.assertNotIn(user, group.get_members())

    def test_unmoderated_messages(self):
        """Test the Group.unmiderated_messages property"""
        group = self.create_group(moderated=False)
        thread = self.create_thread(group=group)

        banned_sender = self.create_user(is_banned=True)
        banned_sender.add_to_group(group.pk)

        regular_sender = self.create_user()
        regular_sender.add_to_group(group.pk)

        banned_pending_message = mommy.make(
            'connectmessages.Message', thread=thread, status='pending',
            sender=banned_sender)

        flagged_message = mommy.make(
            'connectmessages.Message', thread=thread, sender=regular_sender)
        flagged_message.status = 'flagged'
        flagged_message.save()

        pending_message = mommy.make(
            'connectmessages.Message', thread=thread, sender=regular_sender)
        pending_message.status = 'pending'
        pending_message.save()

        normal_message = mommy.make(
            'connectmessages.Message', thread=thread, sender=regular_sender)

        self.assertIn(pending_message, group.unmoderated_messages)
        self.assertIn(flagged_message, group.unmoderated_messages)
        self.assertNotIn(banned_pending_message, group.unmoderated_messages)
        self.assertNotIn(normal_message, group.unmoderated_messages)

    def test_get_members_avatar_prioritized(self):
        """
        Group.get_members_avatar_prioritized() returns users that are in a
        group ordered by if they have an image.
        """
        group = mommy.make(Group)
        image = mommy.make('media.Image')
        user1 = self.create_user()
        user2 = self.create_user(image=image)
        user1.add_to_group(group.pk)
        user2.add_to_group(group.pk)
        members = group.get_members_avatar_prioritized()
        self.assertEqual(user2, members[0])
        self.assertEqual(user1, members[1])

        user1.remove_from_group(group)
        self.assertNotIn(user1, group.get_members_avatar_prioritized())

    @patch.object(models, 'Thread')
    def test_public_threads_by_user(self, mock_thread):
        """Get threads that this user can see for the current group."""
        # Thread.public.by_user is already tested so we'll just verify
        # that the right thing gets called.
        group = mommy.make(Group)
        user = self.create_user()
        group.public_threads_by_user(user)
        mock_thread.public.by_user.assert_called_with(user)
        mock_thread.public.by_user().filter.assert_called_with(group=group)

    @patch.object(models, 'Thread')
    def test_public_threads(self, mock_thread):
        """Test that this gets public threads for this group."""
        # pylint: disable=no-self-use
        # Thread.public.by_group is already tested, so just verify it is called.
        group = mommy.make(Group)
        group.public_threads()
        mock_thread.public.by_group.assert_called_with(group=group)

    def test_is_national(self):
        """Should be True if all geolocation fields are missing."""
        group = Group.objects.create(
            name='some local group', latitude=None, longitude=None, radius=None)
        self.assertTrue(group.is_national)

    def test_is_national_some_geoloc_fields_missing(self):
        """Should be True if any geolocation field is missing."""
        group = Group.objects.create(
            name='some local group', latitude=1, longitude=1, radius=None)
        self.assertTrue(group.is_national)

    def test_is_national_with_geolocated_group(self):
        """Should be false if all geolocation fields are entered."""
        group = Group.objects.create(
            name='some local group', latitude=1, longitude=1, radius=1)
        self.assertFalse(group.is_national)

    def test_delete(self):
        """Test delete method"""
        group = Group.objects.create(name="please don't delete me :(")
        self.assertEqual(group.status, 'active')
        user = self.create_user()
        user.add_to_group(group.pk)
        group.delete()
        group = Group.objects.with_deleted().get(pk=group.pk)
        self.assertEqual(group.status, 'deleted')
        self.assertFalse(group.group.user_set.filter(pk=user.pk).exists())


class GroupOwnersChangedReceiverTest(ConnectTestMixin, TestCase):
    """Tests for group_owners_changed reciever."""
    def test_user_added_gets_permissions(self):
        """When a user is added as owner, they should get new permissions."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        group.owners.add(user)
        self.assertTrue(user.has_perm('accounts.can_initiate_direct_messages'))

    def test_user_added_already_in_group(self):
        """If a user already has owner permissions, shouldn't have any error."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        group.owners.add(user)
        group.owners.add(user)
        self.assertTrue(user.has_perm('accounts.can_initiate_direct_messages'))

    @patch('open_connect.groups.models.cache')
    def test_adding_clears_cache(self, mock):
        """Test that the cache is cleared for each owner added"""
        group = self.create_group()
        user1 = self.create_user()
        user2 = self.create_user()

        group.owners.add(user1)
        group.owners.add(user2)

        mock.delete.assert_any_call(user1.cache_key + 'owned_groups')
        mock.delete.assert_any_call(user2.cache_key + 'owned_groups')

    def test_removing_clears_cache(self):
        """Test that the cache is cleared for each owner removing"""
        group = self.create_group()
        user1 = self.create_user()
        user2 = self.create_user()

        # Because the cache is cleared when we add the user to the group using
        # the same receiver, we should separate out those calls and confirm
        # they happened
        with patch('open_connect.groups.models.cache') as cache_add_mock:
            group.owners.add(user1)
            group.owners.add(user2)
            cache_add_mock.delete.assert_any_call(
                user1.cache_key + 'owned_groups')
            cache_add_mock.delete.assert_any_call(
                user2.cache_key + 'owned_groups')
            self.assertEqual(cache_add_mock.delete.call_count, 2)

        with patch('open_connect.groups.models.cache') as cache_remove_mock:
            group.owners.remove(user1)
            group.owners.remove(user2)
            cache_remove_mock.delete.assert_any_call(
                user1.cache_key + 'owned_groups')
            cache_remove_mock.delete.assert_any_call(
                user2.cache_key + 'owned_groups')
            self.assertEqual(cache_remove_mock.delete.call_count, 2)


class GroupImagesTest(ConnectTestMixin, TestCase):
    """Test images method"""
    def setUp(self):
        """Setup the images test"""
        # Make a popular image and an unpopular image
        self.superuser = self.create_superuser()
        self.popular_image = get_in_memory_image_instance(user=self.superuser)
        self.popular_image.view_count = 10000
        self.popular_image.save()
        self.unpopular_image = get_in_memory_image_instance(user=self.superuser)

    def get_images_message(self, group, images=None):
        """Make a message that has the images in the specified group."""
        # Create a message
        thread = self.create_thread(group=group, sender=self.superuser)
        message = thread.first_message

        # Default images
        if not images:
            images = [self.popular_image, self.unpopular_image]

        # Add images to message
        for image in images:
            message.images.add(image)

        return message

    def test_image_posted_to_group_present(self):
        """An image posted to the group should be present."""
        group = self.create_group()
        message = self.get_images_message(group)
        self.assertQuerysetEqual(
            group.images(user=message.sender).all(),
            [repr(item) for item in message.images.all()],
            ordered=False
        )

    def test_image_posted_to_another_group_not_present(self):
        """An image posted to another group should not be present."""
        group = self.create_group()
        other_group = mommy.make('groups.Group')
        message = self.get_images_message(other_group)
        for image in message.images.all():
            self.assertNotIn(image, group.images(user=message.sender))


class GroupLinksTest(ConnectTestMixin, TestCase):
    """Test the links method"""
    def setUp(self):
        """Setup the links test"""
        # Make a popular link and an unpopular link
        self.popular_link = ShortenedURL(url='http://something.com')
        self.popular_link.click_count = 10000
        self.popular_link.save()
        self.unpopular_link = ShortenedURL.objects.create(
            url='http://somethingelse.com')

    def get_links_message(self, group, links=None):
        """Make a message that has the links in the specified group."""
        # Create a message
        thread = self.create_thread(group=group)
        message = thread.first_message

        # Default links
        if not links:
            links = [self.popular_link, self.unpopular_link]

        # Add links to message
        for link in links:
            message.links.add(link)

        return message

    def test_link_posted_to_group_present(self):
        """An image posted to the group should be present."""
        group = mommy.make('groups.Group')
        message = self.get_links_message(group)
        self.assertQuerysetEqual(
            group.links().all(),
            [repr(item) for item in message.links.all()],
            ordered=False
        )

    def test_link_posted_to_another_group_not_present(self):
        """An image posted to another group should not be present."""
        group = mommy.make('groups.Group')
        other_group = mommy.make('groups.Group')
        message = self.get_links_message(other_group)
        for link in message.links.all():
            self.assertNotIn(link, group.links())


class GroupRequestManagerTest(ConnectTestMixin, TestCase):
    """Group join requests manager tests."""
    def test_unapproved_present(self):
        """Unapproved requests are returned in unapproved method."""
        group_request = GroupRequest.objects.create(
            user=self.create_user(), group=mommy.make('groups.Group'))
        self.assertIn(group_request, GroupRequest.objects.unapproved())

    def test_approved_not_present(self):
        """Approved requests are not returned in unapproved method."""
        group_request = GroupRequest.objects.create(
            user=self.create_user(),
            group=mommy.make('groups.Group'),
            moderated_by=self.create_superuser(),
            moderated_at=now(),
            approved=True
        )
        self.assertNotIn(group_request, GroupRequest.objects.unapproved())

    def test_rejected_not_present(self):
        """Rejected requests are not returned in unapproved method."""
        group_request = GroupRequest.objects.create(
            user=self.create_user(),
            group=mommy.make('groups.Group'),
            moderated_by=self.create_superuser(),
            moderated_at=now(),
            approved=False
        )
        self.assertNotIn(group_request, GroupRequest.objects.unapproved())


class GroupRequestTest(ConnectTestMixin, TestCase):
    """GroupRequest method tests."""
    def test_unicode(self):
        """Unicode conversion returns the expected unicode string."""
        user = mommy.make(
            'accounts.User',
            email='test@test.com',
            first_name='Katherine',
            last_name='Janeway',
            state='IL',
            zip_code='60657'
        )
        group_request = mommy.prepare(GroupRequest, user=user)
        self.assertEqual(
            unicode(group_request),
            u'<a href="{url}">Katherine Janeway (test@test.com / IL, 60657)'
            u' requested to join {group}.</a>'.format(
                url=user.get_absolute_url(),
                group=group_request.group
            )
        )
