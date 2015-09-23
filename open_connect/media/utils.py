"""Media utilities"""
from subprocess import Popen, PIPE

from PIL import Image as PILImage


def resize_gif(image_file, size=(300, 300)):
    """Resize a gif using gifsicle"""
    # pylint: disable=broad-except
    error = False

    # Confirm we're actually dealing with an image
    image_file.seek(0)
    original = PILImage.open(image_file)
    if original.format != 'GIF':
        raise ValueError('Non-GIF File Provided')

    image_file.seek(0)

    try:
        process = Popen(
            [
                'gifsicle',
                '--resize-fit',
                '{width}x{height}'.format(
                    width=int(size[0]), height=int(size[1]))
            ],
            stdin=PIPE, stdout=PIPE
        )
        image_file.seek(0)
        result, _ = process.communicate(image_file.read())

        # If the result is empty, there was an error
        if len(result) == 0:
            error = True
    except Exception:
        # If there straight up was a problem, like the library didn't
        # exist, turn an error to true
        result = ''
        error = True

    return result, error
