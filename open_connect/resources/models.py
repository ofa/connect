"""Models for Connect resources."""
from django_extensions.db.fields import UUIDField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from taggit.managers import TaggableManager

from open_connect.connectmessages.models import DeletedItemsManager
from open_connect.connect_core.utils.models import TimestampModel
from open_connect.connect_core.utils.stringhelp import generate_random_string


RESOURCE_STATUSES = (
    ('active', 'Active'),
    ('deleted', 'Deleted')
)

FILE_TYPE_TO_MIME = {
    'pdf': ['application/pdf'],
    'document': [
        'text/plain', 'application/msword', 'application/rtf',
        'application/x-rtf', 'text/richtext',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.docume'
        'nt',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.templa'
        'te'
    ],
    'spreadsheet': [
        'application/excel', 'application/x-excel',
        'application/msexcel', 'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ],
    'image': [
        'image/png', 'image/gif', 'image/jpeg', 'image/pjpeg',
        'image/bmp', 'image/x-windows-bmp', 'image/webp'
    ],
    'video': [
        'video/mpeg', 'application/x-troff-msvideo',
        'video/avi', 'video/msvideo', 'video/x-msvideo'
        'application/x-shockwave-flash'
    ]
}


MIME_TO_FILE_TYPE = {}
FILE_TYPES = []
for key, values in FILE_TYPE_TO_MIME.iteritems():
    FILE_TYPES.append(key)
    for value in values:
        MIME_TO_FILE_TYPE[value] = key


class Resource(TimestampModel):
    """A single Connect resource."""
    attachment = models.FileField(max_length=255, upload_to='resources')
    content_type = models.CharField(max_length=255, default='text/plain')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, editable=False)
    groups = models.ManyToManyField('groups.Group')
    tags = TaggableManager(blank=True)
    uuid = UUIDField(version=4, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    status = models.CharField(
        max_length=20, choices=RESOURCE_STATUSES, default='active')

    objects = DeletedItemsManager()

    class Meta(object):
        """Meta Options for Resource Model"""
        permissions = (
            ('can_add_resource_anywhere', 'Can create resources anywhere.'),
        )

    def __unicode__(self):
        """Unicode representation of the resource."""
        return self.name

    def get_absolute_url(self):
        """Absolute url to a Resource."""
        return reverse('resource', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        """Save the Resource"""
        if not self.pk:
            self.slug = slugify(unicode(self.name))
            while Resource.objects.filter(slug=self.slug).exists():
                self.slug = u'{name_slug}-{random}'.format(
                    name_slug=slugify(unicode(self.name)),
                    random=generate_random_string()
                )
        return super(Resource, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Mark a resource as deleted."""
        self.status = 'deleted'
        self.save()

    def user_can_download(self, user_id):
        """Does the given user have access to this resource?"""
        return self.groups.filter(
            Q(group__user__pk=user_id) | Q(private=False)
        ).exists()

    def user_can_edit(self, user_id):
        """Can the given user edit this resource?"""
        if self.created_by.pk == user_id:
            return True
        user = get_user_model().objects.get(pk=user_id)
        if user.has_perm('resources.can_add_resource_anywhere'):
            return True
        return False

    def user_can_delete(self, user_id):
        """Can the given user delete this resource?"""
        # For now, this is the same as edit permissions.
        return self.user_can_edit(user_id)

    @property
    def file_type(self):
        """Return the type of file based on content_type."""
        return MIME_TO_FILE_TYPE.get(self.content_type, None)
