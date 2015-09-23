"""Media app tasks"""
# pylint: disable=not-callable, invalid-name
from celery import shared_task


def import_image():
    """Avoid circular dependency import error but still make this mockable."""
    from open_connect.media.models import Image
    return Image


@shared_task(name='process-image')
def process_image(image_id):
    """
    Run any tasks necessary to process a new/updated image
    """
    Image = import_image()
    image = Image.objects.get(pk=image_id)
    image.create_display_size()
    image.create_thumbnail()
    image.process_exif_data()
