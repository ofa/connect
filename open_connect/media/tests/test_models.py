"""Tests for media.models."""
# pylint: disable=maybe-no-member, too-many-instance-attributes
from base64 import urlsafe_b64encode
from unittest import skipIf
import hashlib
import os
import re

from django.core.files import File
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from mock import patch, Mock
from model_mommy import mommy
from PIL import Image as PILImage

from open_connect.media import models
from open_connect.media.models import Image
from open_connect.media.tests.test_utils import gifsicle_not_installed
from open_connect.connect_core.utils.basetests import ConnectTestMixin


class ImageTest(ConnectTestMixin, TestCase):
    """Tests for Image model"""
    def setUp(self):
        super(ImageTest, self).setUp()
        self.path = os.path.dirname(os.path.abspath(__file__))

    def get_image(self, filename):
        """Returns the specified image."""
        path = os.path.join(self.path, filename)
        image = Image()
        image.image = File(open(path))
        image.user = self.create_user()
        image.save(process=False)
        return image

    def get_large_image(self):
        """Returns the large image."""
        return self.get_image('1000x500.png')

    def get_small_image(self):
        """Returns the small image."""
        return self.get_image('200x200.png')

    def get_animated_image(self):
        """Returns the animated GIF"""
        return self.get_image('animation.gif')

    def get_exif_image(self):
        """Returns the exif image"""
        return self.get_image('exif.jpg')

    def test_create_display_size(self):
        """Test creating a display_image."""
        largeimage = self.get_large_image()
        largeimage.create_display_size()
        smallimage = self.get_small_image()
        smallimage.create_display_size()

        # Confirm that the large image was resized, the small was not
        self.assertEqual(smallimage.image, smallimage.display_image)
        self.assertNotEqual(largeimage.image, largeimage.display_image)

        # Confirm that the large image is at or below 600x600
        largeimage.display_image.open()
        large_image_display = PILImage.open(largeimage.display_image)
        self.assertLessEqual(large_image_display.size, (600, 600))

    def test_create_thumbnail(self):
        """Test creating a thumbnail."""
        largeimage = self.get_large_image()
        largeimage.create_thumbnail()

        largeimage.thumbnail.open()
        thumbnail = PILImage.open(largeimage.thumbnail)
        self.assertLessEqual(thumbnail.size, (200, 200))

    @skipIf(gifsicle_not_installed(), 'Gifsicle not installed')
    def test_create_thumbnail_animation(self):
        """Test creating a thumbnail of an animated GIF."""
        # pylint: disable=expression-not-assigned
        animatedimage = self.get_animated_image()
        animatedimage.image.open()
        image = PILImage.open(animatedimage.image)
        # Confirm there are 4 frames by ensuring that the 5th frame raises an
        # error
        [image.seek(frame) for frame in range(0, 4)]
        with self.assertRaises(ValueError):
            image.seek(5)

        animatedimage.create_thumbnail()

        animatedimage.thumbnail.open()
        thumbnail = PILImage.open(animatedimage.thumbnail)
        # Confirm that there are the same number of frames (4) as the original
        [thumbnail.seek(frame) for frame in range(0, 4)]
        with self.assertRaises(ValueError):
            thumbnail.seek(5)
        self.assertLessEqual(thumbnail.size, (200, 200))

    @patch('open_connect.media.models.resize_gif')
    def test_create_thumbnail_animation_no_gifsicle(self, mock_resize):
        """Test resizing an image when gifsicle is not installed"""
        mock_resize.return_value = ('', True)
        animatedimage = self.get_animated_image()

        mock_resize.assert_called_once()

        animatedimage.create_thumbnail()

        # Open both, confirm that the thumbnail is identical to the image
        animatedimage.image.open()
        animatedimage.thumbnail.open()

        # Hash both files to confirm they are the same
        image_hash = hashlib.md5(animatedimage.image.read()).hexdigest()
        thumbnail_hash = hashlib.md5(animatedimage.thumbnail.read()).hexdigest()
        self.assertEqual(image_hash, thumbnail_hash)

    def test_process_exif_data(self):
        """Test grabbing exif data from an image"""
        image = self.get_exif_image()
        image.image = File(open(os.path.join(self.path, 'exif.jpg')))
        image.save()
        self.assertFalse(image.exif)

        image.process_exif_data()

        self.assertTrue(image.exif)

        exif_data = image.exif
        self.assertEqual(exif_data['ExifImageWidth'], 375)
        self.assertEqual(exif_data['ExifImageHeight'], 500)

        self.assertEqual(
            exif_data['LensModel'], u'iPhone 5s back camera 4.15mm f/2.2')
        self.assertEqual(exif_data['Model'], 'iPhone 5s')

    def test_process_exif_data_when_no_data(self):
        """Test process_exif_data when there is no exif data"""
        image = self.get_small_image()
        self.assertFalse(image.exif)
        image.process_exif_data()
        self.assertFalse(image.exif)

    @patch.object(models, 'PILImage')
    def test_process_exif_getexif_returns_none(self, mock_pilimage):
        """If _getexif returns None, don't fail."""
        # pylint: disable=protected-access
        mock_original = Mock()
        mock_original._getexif.return_value = None
        mock_pilimage.open.return_value = mock_original
        image = self.get_small_image()
        image.process_exif_data()
        self.assertEqual(mock_original._getexif.call_count, 1)

    def test_process_exif_raises_unicode_decode_error(self):
        """Handle UnicodeDecodeError gracefully when saving exif."""
        image = self.get_exif_image()
        with patch.object(image, 'save') as mock_save:
            mock_save.side_effect = UnicodeDecodeError(b'utf-8', b'', 0, 1, 'a')
            self.assertIsNone(image.process_exif_data())

    def test_get_thumbnail(self):
        """Test getting the thumbnail."""
        image = self.get_large_image()
        self.assertEqual(image.image, image.get_thumbnail)

        image.create_thumbnail()

        self.assertNotEqual(image.image, image.thumbnail)

    def test_get_display_size(self):
        """Test getting the display size."""
        image = self.get_large_image()
        self.assertEqual(image.image, image.get_display_image)

        image.create_display_size()

        self.assertNotEqual(image.image, image.get_display_image)

    @patch('open_connect.media.models.process_image')
    def test_image_process_called(self, mock):
        """process_image is called when save is called with process=True."""
        image = self.get_small_image()
        image.save(process=True)

        self.assertTrue(mock.delay.called)

    def test_serializable(self):
        """Test serializable method."""
        image = self.get_small_image()
        serialized = image.serializable()
        self.assertEqual(serialized['pk'], image.pk)
        self.assertEqual(
            serialized['image_url'], image.get_absolute_url())
        self.assertEqual(
            serialized['display_image_url'],
            image.get_display_image.url
        )
        self.assertEqual(
            serialized['thumbnail_url'], image.get_thumbnail.url)

    def test_file_name(self):
        """Should return just the name of the file without any path."""
        image = self.get_small_image()
        self.assertTrue(
            re.search(
                r'^[1-4][0-9]{5}\.[0-9a-f]{32}\.png$',
                image.file_name()
            )
        )


class ImagePopularityManagerTest(ConnectTestMixin, TestCase):
    """Tests for the Image Popularity manager"""
    def setUp(self):
        """Setup for image popularity manager tests"""
        self.banned_user = self.create_user(is_banned=True, is_superuser=True)
        self.super_user = self.create_superuser()
        self.normal_user = self.create_user()
        self.group = mommy.make('groups.Group')
        self.banned_user.add_to_group(self.group.pk)
        self.super_user.add_to_group(self.group.pk)
        self.normal_user.add_to_group(self.group.pk)

        self.client.login(username=self.super_user.email, password='moo')

        path = os.path.dirname(os.path.abspath(__file__))
        self.largefile = path + '/1000x500.png'
        self.smallfile = path + '/200x200.png'

        self.largeimage = Image()
        self.largeimage.image = File(open(self.largefile))
        self.largeimage.user = self.super_user
        self.largeimage.save()

        self.smallimage = Image()
        self.smallimage.image = File(open(self.smallfile))
        self.smallimage.user = self.super_user
        self.smallimage.save()

    def test_with_user(self):
        """Should return images attached to approved messages."""
        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=self.group)
        message = mommy.make(
            'connectmessages.Message',
            thread=thread,
            sender=self.normal_user,
            status='approved'
        )

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        result = self.client.get(reverse('admin_gallery'))
        self.assertEqual(result.status_code, 200)
        self.assertIn(image1, result.context['images'])

    def test_with_user_non_group_message(self):
        """Images posted in direct messages shouldn't be returned."""
        # Create a new thread and message
        thread = mommy.make(
            'connectmessages.Thread', group=None, thread_type='direct')
        message = mommy.make(
            'connectmessages.Message',
            thread=thread,
            sender=self.normal_user,
            status='spam'
        )

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        result = self.client.get(reverse('admin_gallery'))
        self.assertEqual(result.status_code, 200)
        self.assertNotIn(image1, result.context['images'])

    def test_with_user_message_not_approved(self):
        """Images that are not approved should not be returned."""
        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=self.group)
        message = mommy.make(
            'connectmessages.Message',
            thread=thread,
            sender=self.normal_user,
            status='spam'
        )

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        result = self.client.get(reverse('admin_gallery'))
        self.assertEqual(result.status_code, 200)
        self.assertIn(image1, result.context['images'])

    def test_with_user_message_not_approved_user_is_sender(self):
        """Images that are not approved should be returned to the sender."""
        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=self.group)
        message = mommy.make(
            'connectmessages.Message',
            thread=thread,
            sender=self.super_user,
            status='spam'
        )

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        result = self.client.get(reverse('admin_gallery'))
        self.assertEqual(result.status_code, 200)
        self.assertIn(image1, result.context['images'])

    def test_with_user_no_images_from_banned_users(self):
        """Images from banned users shouldn't be present."""
        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=self.group)
        message = mommy.make(
            'connectmessages.Message', thread=thread, sender=self.banned_user)

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        result = self.client.get(reverse('admin_gallery'))
        self.assertEqual(result.status_code, 200)
        self.assertNotIn(image1, result.context['images'])

    def test_with_user_current_user_is_banned(self):
        """Images from banned users should be visible to the banned user.."""
        # Create a new thread and message
        thread = mommy.make('connectmessages.Thread', group=self.group)
        message = mommy.make(
            'connectmessages.Message', thread=thread, sender=self.banned_user)

        # Create and attach a new image
        image1 = Image()
        image1.user = message.sender
        image1.image = File(open(self.smallfile))
        image1.save()
        message.images.add(image1)

        client = Client()
        client.post(
            reverse('account_login'),
            {'login': self.banned_user.email, 'password': 'moo'}
        )

        result = client.get(reverse('admin_gallery'))
        self.assertEqual(result.status_code, 200)
        self.assertIn(image1, result.context['images'])


class Base64URLShortenerTest(TestCase):
    """Tests for Base64URLShortener."""
    def setUp(self):
        self.shortener = models.Base64URLShortener()

    def test_shorten(self):
        """Test that shortener returns expected value."""
        result = self.shortener.shorten(123)
        self.assertEqual(result, 'MTIz')

    def test_expand(self):
        """Test that shortener can expand shortened value."""
        result = self.shortener.expand('MTIz')
        self.assertEqual(result, '123')


class ShortenedURLTest(TestCase):
    """Tests for ShortenedURL model."""
    def setUp(self):
        """ShortenURL Test Setup"""
        self.url = models.ShortenedURL.objects.create(
            url='http://www.google.com')

    def test_save_without_short_code(self):
        """Test that saving ShortenedURL sets the short code."""
        self.assertEqual(
            self.url.short_code, urlsafe_b64encode(str(self.url.pk)).strip('='))

    def test_save_with_short_code(self):
        """Test that saving ShortenedURL doesn't override a preset short_code"""
        result = models.ShortenedURL.objects.create(
            url='http://www.thisisanewurl.com',
            short_code='something crazy'
        )
        self.assertEqual(result.short_code, 'something crazy')

    def test_get_absolute_url(self):
        """Test that get_absolute_url returns redirect view."""
        self.assertEqual(
            self.url.get_absolute_url(),
            reverse('shortened_url_redirect',
                    kwargs={'code': self.url.short_code})
        )

    def test_click_increases_click_count(self):
        """Test that click method increments click_count."""
        click_count = self.url.click_count
        self.url.click()
        url = models.ShortenedURL.objects.get(pk=self.url.pk)
        self.assertEqual(url.click_count, click_count + 1)

    def test_click_creates_shortened_url_click(self):
        """Test that click method creates new ShortenedURLClick instance."""
        clicks = self.url.shortenedurlclick_set.count()
        self.url.click()
        url = models.ShortenedURL.objects.get(pk=self.url.pk)
        self.assertEqual(url.shortenedurlclick_set.count(), clicks + 1)

    def test_unicode(self):
        """Test that unicode response is as expected."""
        self.assertEqual(
            unicode(self.url),
            u'ShortenedURL %s: %s' % (self.url.pk, self.url.url)
        )
