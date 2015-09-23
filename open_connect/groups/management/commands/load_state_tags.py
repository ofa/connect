"""Command for loading state abbreviations as tags."""
from django.core.management.base import BaseCommand
from taggit.models import Tag

from open_connect.connect_core.utils.location import STATES


class Command(BaseCommand):
    """Command for loading state abbreviations as tags."""
    def handle(self, *args, **options):
        """Handle command."""
        tags = []
        for state in STATES:
            tags.append(Tag(name=state, slug=state))

        Tag.objects.bulk_create(tags)
