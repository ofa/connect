"""Tests for resources."""
# pylint: disable=invalid-name
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy
import json

from open_connect.media.tests import get_in_memory_image_file
from open_connect.connect_core.utils.basetests import ConnectTestMixin
from open_connect.resources.models import Resource
from open_connect.resources.tests import ResourceMixin


class TestResourceCreateView(ConnectTestMixin, TestCase):
    """Tests for ResourceCreateView."""
    def test_form_valid(self):
        """Test form_valid."""
        group = mommy.make('groups.Group')
        group2 = mommy.make('groups.Group')
        user = self.create_user()
        permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        user.user_permissions.add(permission)
        group.owners.add(user)
        group2.owners.add(user)
        self.login(user)
        response = self.client.post(
            reverse('create_resource'),
            {
                'attachment': get_in_memory_image_file(),
                'name': 'fjkliogaer89u032fjkl',
                'groups': [group.pk, group2.pk]
            }
        )
        self.assertRedirects(response, reverse('resources'))
        resource = Resource.objects.get(name='fjkliogaer89u032fjkl')
        self.assertEqual(resource.content_type, 'image/png')
        self.assertEqual(resource.created_by, user)
        self.assertEqual(resource.groups.count(), 2)

    def test_permission_required_to_create_resource(self):
        """User needs permission to create new resources."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        group.owners.add(user)
        self.login(user)
        response = self.client.post(
            reverse('create_resource'),
            {
                'attachment': get_in_memory_image_file(),
                'name': 'Test resource',
                'groups': [group.pk]
            }
        )
        self.assertEqual(response.status_code, 403)

    def test_user_has_permission_but_is_not_group_owner(self):
        """Users can only create resources for groups they own."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        user.user_permissions.add(permission)
        self.login(user)
        response = self.client.post(
            reverse('create_resource'),
            {
                'attachment': get_in_memory_image_file(),
                'name': 'Test resource',
                'groups': [group.pk]
            }
        )
        self.assertEqual(
            response.context_data['form'].errors,
            {'groups': [
                u'Select a valid choice. '
                u'%s is not one of the available choices.' % group.pk
            ]}
        )

    def test_user_has_super_create_permission(self):
        """Users with elevated permissions can create resources anywhere."""
        group = mommy.make('groups.Group')
        user = self.create_user()
        add_permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        anywhere_permission = Permission.objects.get_by_natural_key(
            'can_add_resource_anywhere', 'resources', 'resource')
        user.user_permissions.add(add_permission, anywhere_permission)
        self.login(user)
        response = self.client.post(
            reverse('create_resource'),
            {
                'attachment': get_in_memory_image_file(),
                'name': 'fjkliogaer89u032fjkl',
                'groups': [group.pk]
            }
        )
        self.assertRedirects(response, reverse('resources'))
        resource = Resource.objects.get(name='fjkliogaer89u032fjkl')
        self.assertTrue(resource.groups.filter(pk=group.pk).exists())


class TestResourceUpdateView(ConnectTestMixin, TestCase):
    """Tests for ResourceUpdateView."""
    def setUp(self):
        """Prepare common items."""
        self.group = mommy.make('groups.Group')
        self.user = self.create_user()
        self.resource = Resource.objects.create(
            attachment=get_in_memory_image_file(),
            name='test resource',
            created_by=self.user
        )
        self.resource.groups.add(self.group)
        self.url = reverse(
            'update_resource', kwargs={'uuid': self.resource.uuid})

    def test_form_valid(self):
        """Test form_valid."""
        permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        self.user.user_permissions.add(permission)
        self.group.owners.add(self.user)
        self.login(self.user)
        old_attachment = self.resource.attachment
        response = self.client.post(
            self.url,
            {
                'attachment': get_in_memory_image_file(),
                'name': 'agafdsafdsagewa',
                'groups': [self.group.pk]
            }
        )
        self.assertRedirects(response, reverse('resources'))
        resource = Resource.objects.get(pk=self.resource.pk)
        self.assertEqual(resource.name, 'agafdsafdsagewa')
        self.assertNotEqual(resource.attachment, old_attachment)

    def test_form_valid_not_updating_file(self):
        """Should be able to submit form without updating the actual file."""
        permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        self.user.user_permissions.add(permission)
        self.group.owners.add(self.user)
        self.login(self.user)
        response = self.client.post(
            self.url,
            {
                'name': 'agafdsafdsagewa',
                'groups': [self.group.pk]
            }
        )
        self.assertRedirects(response, reverse('resources'))
        resource = Resource.objects.get(pk=self.resource.pk)
        self.assertEqual(resource.name, 'agafdsafdsagewa')
        self.assertIsNotNone(resource.attachment)

    def test_only_owner_can_modify_resource(self):
        """Only the creator of a resource should be able to modify it."""
        user = self.create_user()
        permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        user.user_permissions.add(permission)
        self.group.owners.add(user)
        self.login(user)
        response = self.client.post(
            self.url,
            {
                'attachment': get_in_memory_image_file(),
                'name': 'agafdsafdsagewa',
                'groups': [self.group.pk]
            }
        )
        self.assertEqual(response.status_code, 403)

    def test_user_has_super_create_permission_can_modify_any_resource(self):
        """A user with elevated permissions can edit any resource."""
        user = self.create_user()
        add_permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        anywhere_permission = Permission.objects.get_by_natural_key(
            'can_add_resource_anywhere', 'resources', 'resource')
        user.user_permissions.add(add_permission, anywhere_permission)
        self.login(user)
        old_attachment = self.resource.attachment
        response = self.client.post(
            self.url,
            {
                'attachment': get_in_memory_image_file(),
                'name': 'agafdsafdsagewa',
                'groups': [self.group.pk]
            }
        )
        self.assertRedirects(response, reverse('resources'))
        resource = Resource.objects.get(pk=self.resource.pk)
        self.assertEqual(resource.name, 'agafdsafdsagewa')
        self.assertNotEqual(resource.attachment, old_attachment)


class TestResourceListView(ConnectTestMixin, TestCase):
    """Tests for ResourceListView."""
    def test_limited_to_files_for_user(self):
        """Queryset should only include files for groups a user belongs to."""
        user = self.create_user()
        group1 = mommy.make('groups.Group')
        user.add_to_group(group1.pk)
        group2 = mommy.make('groups.Group')
        resource1 = mommy.make('resources.Resource', groups=[group1])
        resource2 = mommy.make('resources.Resource', groups=[group2])

        self.login(user)
        response = self.client.get(reverse('resources'))

        self.assertIn(resource1, response.context_data['resources'])
        self.assertNotIn(resource2, response.context_data['resources'])

    def test_with_query(self):
        """Test seaching by name query."""
        user = self.create_user()
        group1 = mommy.make('groups.Group')
        user.add_to_group(group1.pk)
        group2 = mommy.make('groups.Group')
        user.add_to_group(group2.pk)
        resource1 = mommy.make(
            'resources.Resource', groups=[group1], name='cool thing')
        resource2 = mommy.make(
            'resources.Resource', groups=[group2], name='no way')

        self.login(user)
        response = self.client.get(
            reverse('resources'),
            {'query': 'cool'}
        )

        self.assertIn(resource1, response.context_data['resources'])
        self.assertNotIn(resource2, response.context_data['resources'])

    def test_with_query_tag(self):
        """Test searching by tag."""
        user = self.create_user()
        group1 = mommy.make('groups.Group')
        user.add_to_group(group1.pk)
        group2 = mommy.make('groups.Group')
        user.add_to_group(group2.pk)
        resource1 = mommy.make(
            'resources.Resource', groups=[group1])
        resource1.tags.add('borg')
        resource2 = mommy.make(
            'resources.Resource', groups=[group2])

        self.login(user)
        response = self.client.get(
            reverse('resources'),
            {'query': 'borg'}
        )

        self.assertIn(resource1, response.context_data['resources'])
        self.assertNotIn(resource2, response.context_data['resources'])

    def test_with_group(self):
        """Test searching by group."""
        user = self.create_user()
        group1 = mommy.make('groups.Group')
        user.add_to_group(group1.pk)
        group2 = mommy.make('groups.Group')
        user.add_to_group(group2.pk)
        resource1 = mommy.make(
            'resources.Resource', groups=[group1])
        resource2 = mommy.make(
            'resources.Resource', groups=[group2])

        self.login(user)
        response = self.client.get(
            reverse('resources'),
            {'group_id': group2.pk}
        )

        self.assertNotIn(resource1, response.context_data['resources'])
        self.assertIn(resource2, response.context_data['resources'])

    def test_with_file_type(self):
        """Test searching by file type."""
        user = self.create_user()
        group1 = mommy.make('groups.Group')
        user.add_to_group(group1.pk)
        group2 = mommy.make('groups.Group')
        user.add_to_group(group2.pk)
        resource1 = mommy.make(
            'resources.Resource',
            groups=[group1],
            content_type='application/pdf'
        )
        resource2 = mommy.make(
            'resources.Resource', groups=[group2], content_type='video/avi')

        self.login(user)
        response = self.client.get(
            reverse('resources'),
            {'file_type': 'video'}
        )

        self.assertNotIn(resource1, response.context_data['resources'])
        self.assertIn(resource2, response.context_data['resources'])


class TestResourceDownloadView(ResourceMixin, ConnectTestMixin, TestCase):
    """Tests for ResourceDownloadView."""
    def test_get_redirect_url(self):
        """Test get_redirect_url."""
        resource = self.create_resource()
        self.login(resource.created_by)
        response = self.client.get(
            reverse('resource', kwargs={'slug': resource.slug}))
        # Not using assertRedirects because the file will not be found.
        # Just need to verify that it would redirect to the right place.
        self.assertEqual(
            response['location'],
            'http://testserver{url}'.format(url=resource.attachment.url)
        )

    def test_user_not_in_group_group_is_private(self):
        """Nonmember shouldn't be able to download resource in private group."""
        private_group = mommy.make('groups.Group', private=True)
        resource = self.create_resource(groups=[private_group])

        user = self.create_user()
        self.login(user)
        response = self.client.get(
            reverse('resource', kwargs={'slug': resource.slug}))
        self.assertEqual(response.status_code, 403)


class TestResourceDeleteView(ConnectTestMixin, TestCase):
    """Tests for ResourceDeleteView"""
    def setUp(self):
        """Prepare common items."""
        self.group = mommy.make('groups.Group')
        self.user = self.create_user()
        self.resource = Resource.objects.create(
            attachment=get_in_memory_image_file(),
            name='test resource',
            created_by=self.user
        )
        self.resource.groups.add(self.group)
        self.url = reverse(
            'delete_resource', kwargs={'uuid': self.resource.uuid})

    def test_only_owner_can_delete_resource(self):
        """Only the creator of a resource should be able to delete it."""
        user = self.create_user()
        permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        user.user_permissions.add(permission)
        self.group.owners.add(user)
        self.login(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_user_has_super_create_permission_can_delete_any_resource(self):
        """A user with elevated permissions can delete any resource."""
        user = self.create_user()
        add_permission = Permission.objects.get_by_natural_key(
            'add_resource', 'resources', 'resource')
        anywhere_permission = Permission.objects.get_by_natural_key(
            'can_add_resource_anywhere', 'resources', 'resource')
        user.user_permissions.add(add_permission, anywhere_permission)
        self.login(user)
        response = self.client.post(self.url)
        self.assertEqual(
            json.loads(response.content),
            {'success': True, 'message': 'The resource has been deleted.'}
        )
        resource = Resource.objects.with_deleted().get(pk=self.resource.pk)
        self.assertEqual(resource.status, 'deleted')

    def test_response_is_json(self):
        """After deleting a Resource, return a JSON response."""
        self.login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(
            json.loads(response.content),
            {'success': True, 'message': 'The resource has been deleted.'}
        )
