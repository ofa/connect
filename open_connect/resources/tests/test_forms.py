"""Tests for resources.forms."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from model_mommy import mommy as maker

from open_connect.media.tests import get_in_memory_image_instance
from open_connect.connect_core.utils.basetests import ConnectTestMixin
from open_connect.resources.forms import ResourceForm


class TestResourceForm(ConnectTestMixin, TestCase):
    """Tests for ResourceForm."""
    def test_filename_too_long(self):
        """If the filename is too long, it should trigger an error."""
        user = self.create_user()
        image = get_in_memory_image_instance(user)
        image.image.name = (
            'fjkdslajgdkslajgdlskajfdlskajfldsjafldjsalfkdsjalfkdjsalkfjdsalkjf'
            'dlsakfjdslajfdlksajfdlsajfdlsajfdkslajfdlksajjflkdjlfkjdsklfjaldkj'
            'aflkdjsafkldsjaflkdsjaflkdsjaflkdjsalkfdjsalkfdjsalkfjdsalkfdjsalk'
            'fdjsalkfjdslkajfdlsajfdlasjfdsafdlksajflkdsjalkfjdsalkfjdslakjfsal'
            'fjdsalkfjdslafjdslkajfldsjalfjdslkafjdksalfkdjsalkfjdsa'
        )
        image.save()
        group = maker.make('groups.Group')
        form = ResourceForm(
            data={'name': 'fjkdsl', 'groups': [group.pk]},
            files={
                'attachment': SimpleUploadedFile(
                    image.image.name, image.image.read())
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'attachment': [u'Filename cannot exceed 200 characters.']}
        )
