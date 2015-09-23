"""Tests for Connect resources."""
from django.core.files import File
from model_mommy import mommy

from open_connect.media.tests import get_in_memory_image_file
from open_connect.resources.models import Resource


class ResourceMixin(object):
    """Mixin for easily creating a Resource.

    This mixin requires a create_user method being available, or that user
    is passed to create_resource.
    """
    def create_resource(self, **kwargs):
        """Creates a resource for testing."""
        name = kwargs.get('name', 'test resource')
        if 'user' not in kwargs:
            user = self.create_user()
        else:
            user = kwargs['user']
        if 'groups' not in kwargs:
            groups = [mommy.make('groups.Group')]
            groups[0].owners.add(user)
        else:
            groups = kwargs['groups']
        with File(get_in_memory_image_file()) as tempfile:
            resource = Resource(
                name=name,
                attachment=tempfile,
                created_by=user
            )
            resource.save()
            resource.groups.add(*groups)
        return resource
