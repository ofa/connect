"""Media app task tests"""

from django.test import TestCase
from mock import Mock, patch

from open_connect.media import tasks
from open_connect.media.tests import get_in_memory_image_file


@patch.object(tasks, 'import_image')
class ProcessImageTest(TestCase):
    """Tests for image processing tasks"""
    def test_process_image(self, mock):
        """Testing for process_image task"""
        image_mock = Mock()
        image_mock.image.read.return_value = get_in_memory_image_file().read()
        image_model = Mock()
        image_model.objects.get.return_value = image_mock
        mock.return_value = image_model
        tasks.process_image(image_id=1)
        self.assertEqual(image_mock.create_display_size.call_count, 1)
        self.assertEqual(image_mock.create_thumbnail.call_count, 1)
        self.assertEqual(image_mock.process_exif_data.call_count, 1)
