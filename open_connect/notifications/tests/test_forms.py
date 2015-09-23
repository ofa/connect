"""Tests for notifications.forms."""
from unittest import TestCase

from model_mommy import mommy

from open_connect.notifications.forms import get_subscription_formset


class TestGetSubscriptionFormSet(TestCase):
    """Tests for get_subscription_formset."""
    def test_get_subscription_formset(self):
        """should return a formset with forms for a user."""
        user = mommy.make('accounts.User')
        group1 = mommy.make('groups.Group')
        group2 = mommy.make('groups.Group')
        group3 = mommy.make('groups.Group')
        user.add_to_group(group1.pk)
        user.add_to_group(group2.pk)
        formset = get_subscription_formset(user)
        groups_with_forms = []
        for form in formset:
            groups_with_forms.append(form.instance.group)
            self.assertEqual(form.group_name, form.instance.group.group.name)
        self.assertIn(group1, groups_with_forms)
        self.assertIn(group2, groups_with_forms)
        self.assertNotIn(group3, groups_with_forms)
