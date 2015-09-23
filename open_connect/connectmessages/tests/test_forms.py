"""Tests for connectmessages.forms."""
# pylint: disable=invalid-name
import os

from django.core.files import File
from mock import patch

from open_connect.media.models import Image
from open_connect.connectmessages import forms
from open_connect.connectmessages.models import Message
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.tests.test_utils_mixins import TEST_HTML


class GroupMessageFormTest(ConnectMessageTestCase):
    """Tests for GroupMessageForm."""

    TEST_SUBJECT = 'A Great Message About Cookies'

    def setUp(self):
        """Setup the GroupMessageFormTest TestCase"""
        self.form_data = {
            'group': self.group1.pk,
            'subject': self.TEST_SUBJECT,
            'text': TEST_HTML
        }

    def test_direct_form(self):
        """Test DirectMessageForm."""
        # Create a new form using our custom data
        form_data = {
            'recipients': [self.user1.pk, self.user2.pk],
            'subject': self.TEST_SUBJECT,
            'text': TEST_HTML
        }
        form = forms.DirectMessageForm(form_data)

        # Test to confirm the form is valid
        self.assertEqual(form.is_valid(), True)

    def test_group_form(self):
        """Test GroupMessageForm."""
        # Create a new form using the form data from setUp
        form = forms.GroupMessageForm(self.form_data)

        # Ensure that is_valid is called
        self.assertEqual(form.is_valid(), True)

    @patch.object(forms.SanitizeHTMLMixin, 'sanitize_html')
    def test_form_cleans_html(self, mock):
        """Test that text in form is cleaned"""
        # Create a new form using the form data from setUp
        form = forms.GroupMessageForm(self.form_data)

        # Test to confirm the form is valid
        self.assertEqual(form.is_valid(), True)

        mock.assertCalledWith(TEST_HTML)

    def test_save_returns_message(self):
        """Test save method."""
        form = forms.GroupMessageForm(self.form_data)
        self.assertTrue(form.is_valid())
        form.instance.sender_id = self.user1.pk
        response = form.save()
        self.assertIsInstance(response, Message)

    def test_save_images_added_to_message(self):
        """Test that save adds images to the message."""
        path = os.path.dirname(os.path.abspath(__file__))
        image = Image.objects.create(
            image=File(open(os.path.join(path, '200x200.gif'))),
            user=self.user1
        )
        self.form_data['images'] = [image.pk]
        form = forms.GroupMessageForm(self.form_data)
        form.instance.sender_id = self.user1.pk
        self.assertTrue(form.is_valid(), msg=form.errors)
        result = form.save()
        self.assertTrue(result.images.exists())
