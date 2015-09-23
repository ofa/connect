"""Test the Accounts admin.py file"""
from django.test import RequestFactory, TestCase

from open_connect.accounts.models import User
from open_connect.accounts.admin import UserAdmin, admin as user_admin


class TestUserAdmin(TestCase):
    """Test the UserAdmin modeladmin"""
    def setUp(self):
        """Setup the UserAdmin Test"""
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')

    def test_get_actions(self):
        """Test the get_actions method on the UserAdmin"""
        admin = UserAdmin(User, user_admin.site)
        actions = admin.get_actions(self.request)
        self.assertNotIn('delete_selected', actions)
        self.assertIn('assign_to_perm_group', actions)
