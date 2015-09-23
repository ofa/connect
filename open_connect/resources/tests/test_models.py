"""Tests for resource models."""
from django.contrib.auth.models import Permission
from django.core.files import File
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy

from open_connect.media.tests import get_in_memory_image_file
from open_connect.connect_core.utils.basetests import ConnectTestMixin
from open_connect.resources.models import generate_random_string, Resource


class TestGenerateRandomString(TestCase):
    """Tests for generate_random_string."""
    def test_random_string_no_args(self):
        """Test calling generate_random_string without args."""
        result = generate_random_string()
        self.assertEqual(len(result), 10)

    def test_random_string_with_length(self):
        """Test calling generate_random_string with length."""
        result = generate_random_string(length=3)
        self.assertEqual(len(result), 3)


class TestResource(ConnectTestMixin, TestCase):
    """Tests for Resource model."""
    def test_unicode(self):
        """Test unicode representation of Resource."""
        resource = mommy.make('resources.Resource')
        self.assertEqual(unicode(resource), resource.name)

    def test_get_absolute_url(self):
        """Test getting the absolute url."""
        resource = mommy.make('resources.Resource')
        self.assertEqual(
            resource.get_absolute_url(),
            reverse('resource', kwargs={'slug': resource.slug})
        )

    def test_save_new_resource(self):
        """Test saving a new Resource."""
        with File(get_in_memory_image_file()) as tempfile:
            user = self.create_user()
            resource = Resource(
                name='something cool',
                attachment=tempfile,
                created_by=user
            )
            resource.save()
            self.assertEqual(resource.slug, 'something-cool')

    def test_save_existing_resource(self):
        """Test saving an existing resource."""
        resource = mommy.make('resources.Resource')
        old_slug = resource.slug
        resource.name = 'this is something new!'
        resource.save()
        resource = Resource.objects.get(pk=resource.pk)
        self.assertEqual(resource.name, 'this is something new!')
        self.assertEqual(resource.slug, old_slug)

    def test_save_resource_with_same_name_as_another_resource(self):
        """Should still generate a unique slug."""
        user = self.create_user()
        with File(get_in_memory_image_file()) as tempfile:
            resource = Resource(
                name='wasabi peas',
                attachment=tempfile,
                created_by=user
            )
            resource.save()

        with File(get_in_memory_image_file()) as tempfile:
            new_resource = Resource(
                name='wasabi peas',
                attachment=tempfile,
                created_by=user
            )
            new_resource.save()

        self.assertTrue(new_resource.slug.startswith('wasabi-peas-'))
        self.assertNotEqual(new_resource.slug, resource.slug)

    def test_delete(self):
        """Test deleting a resource."""
        user = self.create_user()
        with File(get_in_memory_image_file()) as tempfile:
            resource = Resource(
                name='wasabi peas',
                attachment=tempfile,
                created_by=user
            )
            resource.save()
        self.assertEqual(resource.status, 'active')
        resource.delete()
        self.assertEqual(resource.status, 'deleted')

    def test_user_has_access_user_in_group(self):
        """Should be True when user is in a group the resource is posted to."""
        group = mommy.make('groups.Group', private=True)
        resource = mommy.make(Resource, groups=[group])
        user = self.create_user()
        user.add_to_group(group.pk)
        self.assertTrue(resource.user_can_download(user.pk))

    def test_user_has_access_group_is_public(self):
        """Should be true when resource is posted to any public group."""
        group = mommy.make('groups.Group', private=False)
        resource = mommy.make(Resource, groups=[group])
        user = self.create_user()
        self.assertTrue(resource.user_can_download(user.pk))

    def test_user_has_access_user_not_in_group_and_no_public_groups(self):
        """False if all resource groups are private and user isn't member."""
        group = mommy.make('groups.Group', private=True)
        resource = mommy.make(Resource, groups=[group])
        user = self.create_user()
        self.assertFalse(resource.user_can_download(user.pk))

    def test_user_can_edit_created_by_user(self):
        """Should be True if Resource was created by this user."""
        user = self.create_user()
        resource = mommy.make(Resource, created_by=user)
        self.assertTrue(resource.user_can_edit(user.pk))

    def test_user_can_edit_user_has_anywhere_perm(self):
        """Should be True if user has can_add_resource_anywhere permission."""
        user = self.create_user()
        permission = Permission.objects.get_by_natural_key(
            'can_add_resource_anywhere', 'resources', 'resource')
        user.user_permissions.add(permission)
        resource = mommy.make(Resource)
        self.assertTrue(resource.user_can_edit(user.pk))

    def test_user_can_edit_user_does_not_have_permission(self):
        """False if user doesn't have elevated permissions and is not owner."""
        user = self.create_user()
        resource = mommy.make(Resource)
        self.assertFalse(resource.user_can_edit(user.pk))

    def test_user_can_delete_created_by_user(self):
        """Should be True if Resource was created by this user."""
        user = self.create_user()
        resource = mommy.make(Resource, created_by=user)
        self.assertTrue(resource.user_can_delete(user.pk))

    def test_user_can_delete_user_has_anywhere_perm(self):
        """Should be True if user has can_add_resource_anywhere permission."""
        user = self.create_user()
        permission = Permission.objects.get_by_natural_key(
            'can_add_resource_anywhere', 'resources', 'resource')
        user.user_permissions.add(permission)
        resource = mommy.make(Resource)
        self.assertTrue(resource.user_can_delete(user.pk))

    def test_user_can_delete_user_does_not_have_permission(self):
        """False if user doesn't have elevated permissions and is not owner."""
        user = self.create_user()
        resource = mommy.make(Resource)
        self.assertFalse(resource.user_can_delete(user.pk))

    def test_file_type(self):
        """Should return the correct file type for a given content type."""
        resource = mommy.make(Resource, content_type='image/gif')
        self.assertEqual(resource.file_type, 'image')

    def test_file_type_unrecognized(self):
        """If content_type isn't defined, should return None."""
        resource = mommy.make(Resource, content_type='drink/pellegrino')
        self.assertIsNone(resource.file_type)
