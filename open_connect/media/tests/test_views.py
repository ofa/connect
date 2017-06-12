"""Tests for media.views."""
# pylint: disable=protected-access,maybe-no-member,invalid-name
import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import Client, TestCase, RequestFactory
from django.test.utils import override_settings
from mock import patch

from open_connect.media.models import Image, ShortenedURL
from open_connect.media.tests import (
    get_in_memory_image_file, get_in_memory_image_instance
)
from open_connect.media.views import (
    image_view, URLPopularityView, AdminGalleryView
)
from open_connect.connectmessages.models import MESSAGE_STATUSES
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class ImageViewsTest(ConnectTestMixin, TestCase):
    """Tests for image_view."""
    def setUp(self):
        """Setup for image views tests"""
        super(ImageViewsTest, self).setUp()
        self.user = self.create_superuser()
        self.client.login(username=self.user.email, password='moo')
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_image_view_increments_view_count(self):
        """Viewing an image should increase the view count."""
        image = get_in_memory_image_instance(self.user)
        image_view(self.request, image.uuid)
        small_image = Image.objects.get(pk=image.pk)
        self.assertEqual(small_image.view_count, 1)

    def test_non_display_image_view_does_not_increment_view_count(self):
        """Viewing an alternate size (thumbnail) should not increment count."""
        image = get_in_memory_image_instance(self.user)
        response = image_view(self.request, image.uuid, image_type='thumbnail')
        self.assertEqual(response.url, image.get_thumbnail.url)
        small_image = Image.objects.get(pk=image.pk)
        self.assertEqual(small_image.view_count, 0)

    @patch('open_connect.media.views.cache')
    def test_image_view_uses_correct_hash_key(self, mock):
        """Viewing an alternate size (thumbnail) should not increment count."""
        mock.get.return_value = None
        image = get_in_memory_image_instance(self.user)
        image.uuid = 'uuid-here'
        image.save()

        response = image_view(
            self.request, image.uuid, image_type='display_image')
        self.assertEqual(response.url, image.get_display_image.url)
        mock.get.assert_called_once_with(
            'imageurlcache_display_image_uuid-here')
        mock.set.assert_called_once_with(
            'imageurlcache_display_image_uuid-here',
            image.get_display_image.url,
            2700
        )
        display_image = Image.objects.get(pk=image.pk)
        self.assertEqual(display_image.view_count, 1)

    @patch('open_connect.media.views.cache')
    def test_image_view_returns_cache_if_possible(self, mock):
        """If possible, return what's in the cache"""
        mock.get.return_value = 'http://razzmatazz.local/great.gif'
        image = get_in_memory_image_instance(self.user)
        image.uuid = 'uuid-here'
        image.save()

        response = image_view(
            self.request, image.uuid, image_type='display_image')
        self.assertEqual(response.url, 'http://razzmatazz.local/great.gif')
        mock.get.assert_called_once_with(
            'imageurlcache_display_image_uuid-here')
        display_image = Image.objects.get(pk=image.pk)
        self.assertEqual(display_image.view_count, 1)

    def test_image_view_redirects_to_image_url(self):
        """image_view should redirect to the actual image url."""
        image = get_in_memory_image_instance(self.user)
        response = self.client.get(
            reverse('image', kwargs={'image_uuid': image.uuid}))
        # assertRedirects doesn't work here because there's no staticfiles
        # in the test client
        self.assertEqual(
            response._headers['location'][1],
            'http://testserver%s' % image.image.url
        )

    def test_upload_photos(self):
        """create_image should return JSON response with filelink and id."""
        response = self.client.post(
            reverse('create_image'),
            {'file': get_in_memory_image_file()}
        )
        json_response = json.loads(response.content)
        self.assertTrue('filelink' in json_response[0].keys())
        self.assertTrue(
            json_response[0]['filelink'].startswith(settings.ORIGIN))
        self.assertTrue('id' in json_response[0].keys())

    def test_upload_photos_invalid(self):
        """uploading an invalid value for image should return an empty list."""
        response = self.client.post(
            reverse('create_image'),
            {'file': 'cookies!'}
        )
        self.assertEqual(json.loads(response.content), [])

    def test_upload_photos_get(self):
        """create_image view should return 405 when request method is GET."""
        response = self.client.get(
            reverse('create_image'),
            {'file': 'cookies!'}
        )
        self.assertEqual(response.status_code, 405)

    def test_my_images(self):
        """my_images should return list of images a user has uploaded."""
        image1 = get_in_memory_image_instance(self.user)
        image2 = get_in_memory_image_instance(self.user)
        response = self.client.get(reverse('my_images'))
        content = json.loads(response.content)
        expected = [
            {u'thumb': image1.get_thumbnail.url,
             u'image': image1.get_absolute_url(),
             u'id': image1.pk},
            {u'thumb': image2.get_thumbnail.url,
             u'image': image2.get_absolute_url(),
             u'id': image2.pk}
        ]
        self.assertEqual(len(content), len(expected))
        for image in content:
            self.assertIn(image, expected)

    def test_promote_image_view(self):
        """promote image view should return json with status and uuid."""
        image = get_in_memory_image_instance(self.user)
        self.assertFalse(image.promoted)
        response = self.client.post(
            reverse('promote_image'), {'uuid': image.uuid})
        result = json.loads(response.content)
        image = Image.objects.get(pk=image.pk)
        self.assertTrue(image.promoted)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['uuid'], image.uuid)

    def test_demote_image_view(self):
        """demote image view should return json with status and uuid."""
        image = get_in_memory_image_instance(self.user)
        image.promoted = True
        image.save()
        response = self.client.post(
            reverse('demote_image'), {'uuid': image.uuid})
        result = json.loads(response.content)
        image = Image.objects.get(pk=image.pk)
        self.assertFalse(image.promoted)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['uuid'], image.uuid)

    def test_promote_image_view_no_permission(self):
        """should redirect to login if user doesn't have permission."""
        user = self.create_user()
        self.login(user)

        response = self.client.post(reverse('promote_image'))
        self.assertRedirects(
            response,
            'http://testserver/user/login/?next=/media/image/promote/',
            fetch_redirect_response=False)

    def test_demote_image_view_no_permission(self):
        """should redirect to login if user doesn't have permission."""
        user = self.create_user()
        self.login(user)

        response = self.client.post(reverse('demote_image'))
        self.assertRedirects(
            response,
            'http://testserver/user/login/?next=/media/image/demote/',
            fetch_redirect_response=False)

    @override_settings(LOGIN_URL=reverse('account_login'))
    def test_promote_image_view_requires_post(self):
        """promote image view should return 405 if http method is get."""
        response = self.client.get(reverse('promote_image'))
        self.assertEqual(response.status_code, 405)

    @override_settings(LOGIN_URL=reverse('account_login'))
    def test_demote_image_view_requires_post(self):
        """demote image view should return 405 if http method is get."""
        response = self.client.get(reverse('demote_image'))
        self.assertEqual(response.status_code, 405)

    @override_settings(LOGIN_URL=reverse('account_login'))
    def test_admin_gallery_requires_permission(self):
        """admin gallery should return 403 if user doesn't have permission."""
        user = self.create_user()
        client = Client()
        client.login(username=user.email, password='moo')
        response = client.get(reverse('admin_gallery'))
        self.assertEqual(response.status_code, 403)

    def test_admin_gallery_does_not_have_direct_message_images(self):
        """admin gallery should not include images from direct messages."""
        image = get_in_memory_image_instance(self.user)
        direct_message = self.create_thread(direct=True)
        direct_message.first_message.images.add(image)
        response = self.client.get(reverse('admin_gallery'))
        self.assertNotContains(response, image.uuid)

    def test_admin_gallery_only_has_images_from_approved_messages(self):
        """Test that admin gallery only has images from approved messages"""
        # pylint: disable=unused-variable
        thread = self.create_thread()
        image = get_in_memory_image_instance(self.user)
        thread.first_message.images.add(image)

        for code, name in MESSAGE_STATUSES:
            thread.first_message.status = code
            thread.first_message.save()

            view = AdminGalleryView()
            view.request = self.factory.get('/')
            view.request.user = self.user
            queryset = view.get_queryset()

            if code == 'approved':
                self.assertIn(image, queryset)
            else:
                self.assertNotIn(image, queryset, msg="Status was %s." % code)


class ShortenedURLRedirectTest(ConnectMessageTestCase):
    """Tests for shortened_url_redirect view."""
    def test_redirects(self):
        """view should redirect user to the correct url."""
        url = ShortenedURL.objects.create(url='http://www.google.com')
        response = self.client.get(
            reverse(
                'shortened_url_redirect',
                kwargs={'code': url.short_code}
            )
        )
        self.assertEqual(response['Location'], 'http://www.google.com')

    def test_increases_click_count(self):
        """view should increment click_count by one."""
        url = ShortenedURL.objects.create(url='http://www.google.com')
        click_count = url.click_count
        self.client.get(
            reverse(
                'shortened_url_redirect',
                kwargs={'code': url.short_code}
            )
        )
        url = ShortenedURL.objects.get(pk=url.pk)
        self.assertEqual(url.click_count, click_count + 1)


class URLPopularityViewTest(ConnectMessageTestCase):
    """Tests for URLPopularityView."""
    def setUp(self):
        """Setup the URLPopularityViewTest TestCase"""
        self.view = URLPopularityView()

    def test_order_by_accepts_valid_values(self):
        """order_by in query params should sort by valid values."""
        for value in ['message_count', 'url', 'short_code', 'created_at']:
            request = self.request_factory.get('/?order_by=%s' % value)
            self.view.request = request
            result = self.view.get_queryset()
            self.assertEqual(result.query.order_by, ['-%s' % value])

    def test_order_by_defaults_to_click_count(self):
        """if there is no order_by in query, default to click_count."""
        request = self.request_factory.get('/')
        self.view.request = request
        result = self.view.get_queryset()
        self.assertEqual(result.query.order_by, ['-click_count'])

    def test_order_by_is_click_count_if_value_is_invalid(self):
        """if order_by isn't a valid value, order by click_count."""
        request = self.request_factory.get('/?order_by=invalid')
        self.view.request = request
        result = self.view.get_queryset()
        self.assertEqual(result.query.order_by, ['-click_count'])

    def test_order_is_asc(self):
        """if order is asc, queryset should be sorted ascending."""
        request = self.request_factory.get('/?sort=asc')
        self.view.request = request
        result = self.view.get_queryset()
        self.assertEqual(result.query.order_by, ['click_count'])

    def test_order_is_desc(self):
        """if order is desc, queryset should be sorted descending."""
        request = self.request_factory.get('/?sort=desc')
        self.view.request = request
        result = self.view.get_queryset()
        self.assertEqual(result.query.order_by, ['-click_count'])

    def test_order_is_other(self):
        """if order is invalid, default to descending."""
        request = self.request_factory.get('/?sort=cows!')
        self.view.request = request
        result = self.view.get_queryset()
        self.assertEqual(result.query.order_by, ['-click_count'])

    def test_get_context_data_query_string_removes_order_and_order_by(self):
        """order and order_by keys should be removed from query string."""
        request = self.request_factory.get('/?sort=desc&order_by=url')
        self.view.request = request
        self.view.kwargs = {}
        result = self.view.get_context_data(
            object_list=ShortenedURL.objects.all())
        self.assertEqual(result['query_string'], '')

    def test_get_context_data_query_string_has_other_values(self):
        """
        querystring in context should have any values that aren't filtered
        """
        request = self.request_factory.get('/?sort=desc&order_by=url&cow=moo')
        self.view.request = request
        self.view.kwargs = {}
        result = self.view.get_context_data(
            object_list=ShortenedURL.objects.all())
        self.assertEqual(result['query_string'], 'cow=moo')

    def test_get_context_data_query_string_is_empty(self):
        """
        query_string in context should be empty if there's no query string
        """
        request = self.request_factory.get('/')
        self.view.request = request
        self.view.kwargs = {}
        result = self.view.get_context_data(
            object_list=ShortenedURL.objects.all())
        self.assertEqual(result['query_string'], '')
