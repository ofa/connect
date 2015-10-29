"""Tests for context_processors.connect_processor."""
from django.core.urlresolvers import reverse
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from mock import patch

from open_connect.context_processors.connect_processor import connect_processor
from open_connect.media.models import Image
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class TestConnectProcessor(ConnectTestMixin, ConnectMessageTestCase):
    """Tests for context_processors.connect_processor."""
    def create_object_patch(self, obj, name):
        """Utility method for patching an object."""
        patcher = patch.object(obj, name)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    def test_authenticated_nav(self):
        """Test processor with an authenticated user."""
        user = self.create_user()
        request = self.request_factory.get('/')
        request.user = user
        response = connect_processor(request)
        self.assertEqual(response['nav_items'][0]['label'], 'Messages')
        self.assertEqual(response['nav_items'][0]['link'], reverse('threads'))
        self.assertEqual(response['nav_items'][1]['label'], 'Explore')
        self.assertEqual(response['nav_items'][1]['link'], reverse('explore'))
        self.assertEqual(response['nav_items'][2]['label'], 'Resources')
        self.assertEqual(
            response['nav_items'][2]['link'], reverse('resources'))

        self.assertEqual(response['nav2_items'][0]['label'], 'My Profile')
        self.assertEqual(
            response['nav2_items'][0]['link'], reverse('user_profile'))

        self.assertEqual(
            response['nav2_items'][1]['label'], 'Manage My Account')
        self.assertEqual(
            response['nav2_items'][1]['link'],
            reverse('update_user', args=(user.uuid,)))

        self.assertEqual(
            response['nav2_items'][2]['label'], 'Logout')
        self.assertEqual(
            response['nav2_items'][2]['link'], reverse('logout'))

    @override_settings(LOGIN_URL='/login/')
    def test_unauthenticated_nav(self):
        """Test processor with an unauthenticated user."""
        request = self.request_factory.get('/')
        request.user = AnonymousUser()
        response = connect_processor(request)
        self.assertEqual(response['nav_items'], [])
        self.assertEqual(response['nav2_items'][0]['label'], 'Login')
        self.assertEqual(
            response['nav2_items'][0]['link'], '/login/')

    def test_is_moderator(self):
        """Test processor with when user is a moderator."""
        request = self.request_factory.get('/')
        request.user = self.superuser
        mock_get_moderation_tasks = self.create_object_patch(
            self.request.user, 'is_moderator'
        )
        mock_get_moderation_tasks.return_value = True
        response = connect_processor(self.request)
        self.assertEqual(
            response['nav_items'][-2]['label'], 'Admin')
        self.assertEqual(
            response['nav_items'][-2]['menu'][0]['label'],
            'Message Moderation'
        )
        self.assertEqual(
            response['nav_items'][-2]['menu'][0]['link'],
            reverse('mod_admin')
        )
        self.assertEqual(
            response['nav_items'][-2]['menu'][1]['label'],
            'Flag Moderation Log'
        )
        self.assertEqual(
            response['nav_items'][-2]['menu'][1]['link'],
            reverse('flag_log')
        )
        self.assertEqual(
            response['nav_items'][-2]['menu'][2]['label'],
            'Group Moderation'
        )
        self.assertEqual(
            response['nav_items'][-2]['menu'][2]['link'],
            reverse('moderate_requests')
        )

    @override_settings(BRAND_TITLE='The Test Brand')
    def test_brand_title(self):
        """Test brand title."""
        response = connect_processor(self.request)
        self.assertEqual(response['brand_title'], 'The Test Brand')

    def test_user_has_access_to_admin_gallery(self):
        """Test processor with access to the admin gallery."""
        content_type = ContentType.objects.get_for_model(Image)
        permission = Permission.objects.get(
            content_type=content_type, codename='can_access_admin_gallery')
        self.user2.user_permissions.add(permission)
        request = self.request_factory.get('/')
        request.user = self.user2
        response = connect_processor(request)
        self.assertEqual(
            response['nav_items'][-2]['menu'][0]['label'], 'Admin Gallery')
        self.assertEqual(
            response['nav_items'][-2]['menu'][0]['link'],
            reverse('admin_gallery')
        )
