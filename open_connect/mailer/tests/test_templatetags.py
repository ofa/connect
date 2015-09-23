"""Test mailer templatetags"""
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch
from model_mommy import mommy

from open_connect.mailer.tests.test_utils import OPEN_DATA
from open_connect.mailer.templatetags.mailing import (
    tracking_pixel, email_image_max_width
)


class TestEmailImage(TestCase):
    """Tests for email_image_max_width"""
    @override_settings(ORIGIN='http://connect.local', EMAIL_SECRET_KEY='abcd')
    def test_email_image_max_width(self):
        """Test the max_width templatetag"""
        image = mommy.make('media.Image', image_width=500, image_height=1000)
        image_url = 'http://connect.local' + reverse(
            'custom_image_version',
            kwargs={'image_uuid': image.uuid, 'image_type': 'display_image'})
        result = email_image_max_width(image, 300, 'style="margin: 0 auto;"')
        self.assertIn(image_url, result)
        self.assertIn('width="300"', result)

        # Since 300 is 60% of 500, we need to use 60% of 1000 as the height
        self.assertIn('height="600"', result)
        # Always make sure border="0" is in the tag!
        self.assertIn('border="0"', result)

        # Make sure that our 'extras' are in the tag, padded by spaces
        self.assertIn(' style="margin: 0 auto;" ', result)


class TestTrackingPixel(TestCase):
    """Tests for TrackingPixel"""
    @override_settings(ORIGIN='https://connect.local')
    @patch('open_connect.mailer.templatetags.mailing.generate_code')
    @patch('open_connect.mailer.templatetags.mailing.now')
    @patch('open_connect.mailer.templatetags.mailing.url_representation_encode')
    def test_tracking_pixel(self, mock_url_rep, mock_now, mock_generate_code):
        """Test for tracking pixel"""
        mock_url_rep.return_value = ('VerifiedDataHere', 'HashIsHere')
        mock_generate_code.return_value = 'uLSbgASwWk'
        mock_now().replace(
            ).isoformat.return_value = '2014-04-07 17:01:12+00:00'

        result = tracking_pixel('me@razzmatazz.local', '10')
        mock_url_rep.assert_called_once_with(OPEN_DATA)

        gif_url = reverse(
            'email_open',
            kwargs={
                'encoded_data': 'VerifiedDataHere',
                'request_hash': 'HashIsHere'
            }
        )
        pixel_code = ('<img src="{origin}{gif}" width="1" height="1"'
                      ' border="0">').format(origin='https://connect.local',
                                             gif=gif_url)

        self.assertIn(pixel_code, result)
