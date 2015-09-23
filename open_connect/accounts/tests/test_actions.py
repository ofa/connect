"""Test actions.py in the Accounts app"""
from django.contrib.auth.models import Group as AuthGroup
from django.test import RequestFactory, TestCase
from model_mommy import mommy
from mock import Mock

from open_connect.accounts.models import User
from open_connect.accounts.actions import assign_to_perm_group


class TestAssignToPermGroup(TestCase):
    """Test assign_to_perm_group"""
    def setUp(self):
        """Setup the UserAdmin Test"""
        self.user1 = mommy.make(User)
        self.user2 = mommy.make(User)

        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')
        setattr(self.request, 'user', self.user1)
        self.queryset = User.objects.filter(
            pk__in=[self.user1.pk, self.user2.pk])

    def test_get(self):
        """Test a valid GET request to the action"""
        group = mommy.make(AuthGroup)
        response = assign_to_perm_group(Mock(), self.request, self.queryset)

        self.assertContains(response, str(group))
        self.assertContains(response, str(self.user1))
        self.assertContains(response, 'value="assign_to_perm_group"')
        self.assertEqual(self.queryset, response.context_data['queryset'])

    def test_post(self):
        """Test a valid POST request to the action"""
        group = mommy.make(AuthGroup)
        post_vars = {
            'post': 'true',
            'permission_group': group.pk,
            'users': [user.pk for user in self.queryset]
        }
        request = self.request_factory.post('/', post_vars)

        self.assertNotIn(self.user1, group.user_set.all())
        self.assertNotIn(self.user2, group.user_set.all())

        response = assign_to_perm_group(Mock(), request, self.queryset)

        self.assertIsNone(response)
        self.assertIn(self.user1, group.user_set.all())
        self.assertIn(self.user2, group.user_set.all())

    def test_improper_group_post(self):
        """Test a post where the PK is a group from the group app"""
        improper_group = mommy.make('groups.Group')
        post_vars = {
            'post': 'true',
            'permission_group': improper_group.group.pk
        }
        request = self.request_factory.post('/', post_vars)

        response = assign_to_perm_group(Mock(), request, self.queryset)
        self.assertEqual(
            response.context_data['form'].errors,
            {
                'permission_group': [
                    u'Select a valid choice. That choice'
                    u' is not one of the available choices.'
                ],
                'users': [u'This field is required.']
            }
        )
