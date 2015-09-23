"""Models for the media application."""
# pylint: disable=maybe-no-member,no-self-use

from base64 import urlsafe_b64decode, urlsafe_b64encode
from cStringIO import StringIO
import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Q
from django_extensions.db.fields import UUIDField
from PIL import Image as PILImage, ExifTags
from jsonfield import JSONField

from open_connect.media.tasks import process_image
from open_connect.media.utils import resize_gif
from open_connect.media.validators import validate_unique_url
from open_connect.connect_core.utils.models import TimestampModel
from open_connect.connect_core.utils.storages import (
    HighValueStorage
)


class ImagePopularityManager(models.Manager):
    """Manager for getting popular images."""
    def get_queryset(self):
        """Default queryset for this manager."""
        return super(
            ImagePopularityManager, self
        ).get_queryset().order_by('-promoted', '-view_count')

    def with_user(self, user):
        """Get images that a user has access to."""
        return self.get_queryset().filter(
            Q(message__status='approved')
            | Q(message__sender=user),
            Q(message__sender__is_banned=False)
            | Q(message__sender=user),
            message__thread__group__isnull=False,
        )


class Image(TimestampModel):
    """Generic image model."""
    image = models.ImageField(
        upload_to='attachments/images/',
        height_field='image_height',
        width_field='image_width',
        max_length=250,
        blank=True
    )
    # Friendly Thumbnail (Max 600px by 600px)
    display_image = models.ImageField(
        upload_to='attachments/images/',
        storage=HighValueStorage(),
        max_length=250,
        blank=True
    )
    # Thumbnail of the image. Not required
    thumbnail = models.ImageField(
        upload_to='attachments/thumbnails/images/',
        storage=HighValueStorage(),
        max_length=250,
        blank=True
    )

    # Image data
    exif = JSONField(blank=True, null=True)
    image_height = models.IntegerField(editable=False)
    image_width = models.IntegerField(editable=False)

    view_count = models.PositiveIntegerField(default=0)
    promoted = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='images')
    uuid = UUIDField(version=4, db_index=True)

    objects = models.Manager()
    popular = ImagePopularityManager()

    class Meta(object):
        """Meta options for Image model."""
        get_latest_by = 'created_at'
        ordering = ['-promoted', '-created_at']
        permissions = (
            ('can_promote_image', 'Can promote an image'),
            ('can_access_admin_gallery', 'Can access the admin gallery')
        )

    def __unicode__(self):
        """Unicode representation of Image."""
        return "Image uploaded by {user}".format(user=self.user)

    def get_absolute_url(self):
        """The url to an instance of an Image."""
        return reverse('image', kwargs={'image_uuid': self.uuid})

    def save(self, *args, **kwargs):
        """Override save to trigger image processing tasks."""
        process = kwargs.pop('process', True)
        super(Image, self).save(*args, **kwargs)
        if process:
            process_image.delay(self.pk)

    def create_thumbnail(self, size=(200, 200)):
        """Generate an image thumbnail."""
        uploadfile, filename = self._resize(size=size)

        # Upload the file, set the URL to the ImageField
        self.thumbnail.save(content=uploadfile, name=filename, save=False)

        # Save the model
        self.save(process=False, update_fields=['thumbnail'])

    def create_display_size(self, size=(600, 600)):
        """Generate an image copy that is appropriate for display."""
        # Confirm we actually have an image on this model
        if self.image is None:
            return

        name_format = '{name}_display.{extension}'

        # Check to see if the image is already smaller than our display size
        if (self.image_width, self.image_height) >= size:
            uploadfile, filename = self._resize(
                size=size,
                filename_format=name_format
            )
            self.display_image.save(
                content=uploadfile, name=filename, save=False)
        else:
            # The image is smaller than our display size, simply assign the
            # display_image imagefield to the image
            self.display_image = self.image

        # Save The Model
        self.save(process=False, update_fields=['display_image'])

    def process_exif_data(self):
        """Extract EXIF data from the image and add it to the model"""
        # pylint: disable=protected-access
        # Re-open the image
        self.image.open()
        image_file = StringIO(self.image.read())
        image_file.seek(0)

        # Open the image
        original = PILImage.open(image_file)

        # Find out if it is an image with EXIF data
        if hasattr(original, '_getexif'):
            exif = original._getexif()
            if exif:
                # Match the EXIF field codes to the tag name
                self.exif = {
                    ExifTags.TAGS[code]: value
                    for (code, value) in original._getexif().items()
                    if code in ExifTags.TAGS
                }

                try:
                    # Save the image
                    self.save(process=False, update_fields=['exif'])
                except UnicodeDecodeError:
                    # Oh well
                    pass

        # Close out the file
        image_file.close()

    def _resize(self, size, filename_format=None):
        """Resizes the image"""

        if not filename_format:
            filename_format = '{name}_{width}x{height}.{extension}'

        # Re-open the image
        self.image.open()
        image_file = StringIO(self.image.read())
        image_file.seek(0)

        # Open the image
        original = PILImage.open(image_file)

        # Detect the image type
        pil_type = original.format
        if pil_type == 'JPEG':
            django_type = 'image/jpeg'
            file_extension = 'jpg'
        elif pil_type == 'PNG':
            django_type = 'image/png'
            file_extension = 'png'
        elif pil_type == 'GIF':
            django_type = 'image/gif'
            file_extension = 'gif'
        else:
            django_type = 'image/jpeg'
            file_extension = 'jpg'

        temp_handle = StringIO()

        if pil_type == 'GIF':
            # Process Gif
            result, error = resize_gif(image_file, size)
            if not error:
                temp_handle.write(result)
            else:
                # If something went wrong, use the original file
                temp_handle = image_file
        else:
            # Create the thumbnail
            original.thumbnail(size, PILImage.ANTIALIAS)
            original.save(temp_handle, pil_type)

        temp_handle.seek(0)

        # Create a SimpleUploadFile we can pass to the django ImageField
        suf = SimpleUploadedFile(
            name=os.path.split(self.image.name)[-1],
            content=temp_handle.read(),
            content_type=django_type
        )

        # Close out the files
        image_file.seek(0)
        temp_handle.close()
        image_file.close()

        # Generate the filename of our thumbnail
        filename = filename_format.format(
            name=os.path.splitext(suf.name)[0],
            width=size[0],
            height=size[1],
            extension=file_extension
        )

        return suf, filename

    @property
    def get_thumbnail(self):
        """
        Method that returns a thumbnail of the object, falling back to the
        original image if a thumbnail has not yet been created.
        """
        if self.thumbnail:
            return self.thumbnail
        else:
            return self.image

    @property
    def get_display_image(self):
        """
        Method that returns a displayable size image, falling back to the
        original image if the display-sized image has not been created.
        """
        if self.display_image:
            return self.display_image
        else:
            return self.image

    def serializable(self):
        """Serializable representation of Image."""
        return {
            'pk': self.pk,
            'image_url': self.get_absolute_url(),
            'display_image_url': self.get_display_image.url,
            'thumbnail_url': self.get_display_image.url,
        }

    def file_name(self):
        """Returns the file name for the image (without the path.)"""
        return os.path.split(self.image.name)[-1]


class Base64URLShortener(object):
    """URL Shortener using Base64 to shorten."""
    def shorten(self, value):
        """Shorten a string."""
        # Sliced to remove padding
        return urlsafe_b64encode(str(value)).strip('=')

    def expand(self, value):
        """Expand a B64 string to it's original value."""
        # Add padding back
        return urlsafe_b64decode(str(value).ljust(4, '='))


class ShortenedURLPopularityManager(models.Manager):
    """Manager for getting most popular ShortenedURLs."""
    def get_queryset(self):
        """Get the query set ordered by both click and message counts desc"""
        return super(
            ShortenedURLPopularityManager, self
        ).get_queryset().order_by('-click_count', '-message_count')


class ShortenedURL(TimestampModel):
    """Model for URL redirects."""
    url = models.TextField(validators=[URLValidator(), validate_unique_url])
    short_code = models.CharField(
        max_length=20, blank=True, db_index=True, unique=True)
    click_count = models.PositiveIntegerField(default=0)
    message_count = models.PositiveIntegerField(default=0)

    objects = models.Manager()
    popular = ShortenedURLPopularityManager()

    url_shortener = Base64URLShortener()

    class Meta(object):
        """Meta options for ShortenedURL"""
        get_latest_by = 'created_at'
        permissions = (
            ('can_access_popular_urls', 'Can access the popular url list'),
        )

    def __unicode__(self):
        """Unicode representation of a ShortenedURL."""
        return 'ShortenedURL %s: %s' % (self.pk, self.url)

    def save(self, *args, **kwargs):
        """Override save to add short_code."""
        shortened_url = super(ShortenedURL, self).save(*args, **kwargs)
        # Shortening has to happen after there's a key
        if not self.short_code:
            self.short_code = self.url_shortener.shorten(str(self.pk))
            self.save()
        return shortened_url

    def get_absolute_url(self):
        """URL to a ShortenedURL."""
        return reverse(
            'shortened_url_redirect', kwargs={'code': self.short_code})

    def click(self):
        """Track a click on a ShortenedURL."""
        self.click_count += 1
        self.save()
        self.shortenedurlclick_set.create()


class ShortenedURLClick(TimestampModel):
    """Model for storing click data for ShortenedURL."""
    shortened_url = models.ForeignKey(ShortenedURL)
