"""Media test library."""
# pylint: disable=protected-access
from StringIO import StringIO
from PIL import Image as PILImage

from mock import Mock

from open_connect.media.models import Image
from open_connect.connect_core.utils.stringhelp import generate_random_string


def get_in_memory_image_file():
    """Returns a fake image file. Faster than using file system."""
    image_file = StringIO()
    image = PILImage.new("RGBA", size=(50, 50), color=(256, 0, 0))
    image.save(image_file, 'png')
    name = '%s.png' % generate_random_string()
    image_file.name = name
    image_file.width = 200
    image_file.height = 200
    image_file._committed = False
    image_file.save = Mock()
    image_file.url = '/uploads/%s' % name
    image_file.__unicode__ = Mock(return_value=name)
    image_file.seek(0)
    return image_file


def get_in_memory_image_instance(user):
    """Returns an instance of Image with an in-memory image."""
    image = Image()
    image.image = get_in_memory_image_file()
    image.user = user
    image.save()
    return image
