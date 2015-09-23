"""Tests for groups utilities."""

from unittest import TestCase
from model_mommy import mommy

from open_connect.groups.models import Category, Group
from open_connect.groups.utils import (
    groups_string, groups_tags_string, groups_categories_string
)


class GroupsUtilitiesTest(TestCase):
    """Tests for groups utilities."""
    @classmethod
    def setUpClass(cls):
        """Setup GroupsUtilitiesTest TestCase"""
        # Delete all non-default categories to prevent conflicts on unique
        # `slug` field
        Category.objects.exclude(pk=1).delete()

        cls.lgbt_category = mommy.make(
            'groups.Category', slug='lgbt', name='Expanding Equality')
        cls.fiscal_category = mommy.make(
            'groups.Category', slug='fiscal', name='Economic Opportunity')

        cls.group1 = Group.objects.create(
            name='One', category=cls.lgbt_category)
        cls.group2 = Group.objects.create(
            name='Two', category=cls.fiscal_category)
        cls.group3 = Group.objects.create(
            name='Three', category=cls.fiscal_category)
        cls.groups = [cls.group1, cls.group2, cls.group3]

    def test_groups_string(self):
        """Should be a comma separated list of group names."""
        self.assertEqual(groups_string(self.groups), 'One, Two, Three')

    def test_groups_tags_string(self):
        """Should be a comma separated list of tags for the groups."""
        self.group1.tags.add('moo', 'cow')
        self.group2.tags.add('moo', 'cold')
        self.group3.tags.add('hungry')
        groups_tags = groups_tags_string(self.groups)
        for tag in ['moo', 'cow', 'cold', 'hungry']:
            self.assertIn(tag, groups_tags)

    def test_groups_categories_string(self):
        """Should be comma separated display names for each groups category."""
        self.assertEqual(
            groups_categories_string(self.groups),
            'Expanding Equality, Economic Opportunity, Economic Opportunity'
        )
