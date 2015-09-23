"""Tests for group forms."""
# pylint: disable=invalid-name
from datetime import datetime
from unittest import TestCase

from taggit.models import Tag
from mock import patch, call
from model_mommy import mommy

from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.groups import forms
from open_connect.groups.models import Group, GroupRequest
from open_connect.connect_core.tests.test_utils_mixins import TEST_HTML


class GroupRequestFormTest(ConnectMessageTestCase):
    """Tests for GroupRequestForm."""
    @patch('open_connect.groups.tasks.send_system_message')
    def test_save_approve(self, mock):
        """Test that save does the right thing if approving."""
        group = mommy.make('groups.Group', group__name='Cool Group')
        group_request = GroupRequest.objects.create(
            user=self.user2, group=group)
        form = forms.GroupRequestForm({
            'open_requests': [group_request.pk],
            'action': 'approve'
        })
        self.assertTrue(form.is_valid())
        form.save(user=self.user1)

        group_request = GroupRequest.objects.get(pk=group_request.pk)
        self.assertEqual(group_request.moderated_by, self.user1)
        self.assertIsInstance(group_request.moderated_at, datetime)
        self.assertTrue(group_request.approved)
        self.assertIn(group.group, self.user2.groups.all())
        self.assertTrue(mock.delay.called)

        message_args = mock.delay.call_args[0]
        self.assertEqual(message_args[0], self.user2.pk)
        self.assertEqual(message_args[1], u"You've been added to Cool Group")
        self.assertIn(group.full_url, message_args[2])

    def test_save_reject(self):
        """Test that save does the right thing if rejecting."""
        group_request = GroupRequest.objects.create(
            user=self.user2, group=self.group)
        form = forms.GroupRequestForm({
            'open_requests': [group_request.pk],
            'action': 'reject'
        })
        self.assertTrue(form.is_valid())
        form.save(user=self.user1)
        group_request = GroupRequest.objects.get(pk=group_request.pk)
        self.assertEqual(group_request.moderated_by, self.user1)
        self.assertIsInstance(group_request.moderated_at, datetime)
        self.assertFalse(group_request.approved)
        self.assertNotIn(self.group.group, self.user2.groups.all())


class GroupFormTest(ConnectMessageTestCase):
    """"Tests for GroupForm."""
    def setUp(self):
        """Setup the GroupFormTest"""
        self.category = mommy.make('groups.Category')

    def test_clean_tags_with_valid_tags(self):
        """Form should validate if submitted with valid tags."""
        Tag.objects.create(name='these')
        Tag.objects.create(name='are')
        Tag.objects.create(name='valid')
        Tag.objects.create(name='tags')
        form = forms.GroupForm(
            {
                'tags': 'these,are, valid, tags',
                'category': self.category.pk
            })
        self.assertTrue(form.is_valid())

    def test_clean_tags_with_invalid_tags(self):
        """Form should have errors if submitted with invalid tags."""
        form = forms.GroupForm(
            {
                'tags': 'this,is,an,invalid,tag,list',
                'category': self.category.pk
            })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['tags'],
            [u'These tags are invalid: an, invalid, is, list, tag, this.']
        )

    @patch('open_connect.groups.forms.add_user_to_group')
    def test_owners_added_to_group(self, mock):
        """Test that owners are added to the group"""
        form = forms.GroupForm(
            {
                'owners': [self.user1.pk, self.user2.pk],
                'category': self.category.pk
            },
            instance=self.group1
        )
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(mock.delay.call_count, 2)

        call_list = mock.delay.call_args_list
        self.assertItemsEqual(
            call_list,
            [call(self.user1.pk, self.group1.pk),
             call(self.user2.pk, self.group1.pk)]
        )

    @patch.object(forms.SanitizeHTMLMixin, 'sanitize_html')
    def test_clean_description(self, mock):
        """Test the clean_description cleaner"""
        # pylint: disable=no-self-use
        group = mommy.make(Group)
        form = forms.GroupForm(
            {
                'description': TEST_HTML,
                'category': self.category.pk
            },
            instance=group
        )
        form.is_valid()
        mock.assertCalledWith(TEST_HTML)


class GroupInviteFormTest(TestCase):
    """Tests for GroupInviteForm"""
    def test_invalid_emails_cause_error(self):
        """Test that passing in an invalid email causes an error"""
        form = forms.GroupInviteForm({'emails': 'abcd123123'})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['emails'],
            [u'No Valid Addresses Found'])

    def test_valid_address_go_through(self):
        """Test that passing in a valid email address works"""
        form = forms.GroupInviteForm({'emails': 'me@razzmatazz.local'})
        self.assertTrue(form.is_valid())

    def test_multiple_addresses(self):
        """Test that multiple addresses go through"""
        # pylint: disable=line-too-long
        emails = 'me@razzmatazz.local, m@razzmatazz.local, Adam <adam@gmail.com>'
        form = forms.GroupInviteForm({'emails': emails})
        self.assertTrue(form.is_valid())


class GroupDeleteFormTest(TestCase):
    """Tests for GroupDeleteForm."""
    def test_yes(self):
        """Group should be deleted if the answer is yes."""
        group = Group.objects.create(name='yes')
        form = forms.GroupDeleteForm({'are_you_sure': 'yes'})
        form.group = group
        self.assertTrue(form.is_valid())
        form.save()
        group = Group.objects.with_deleted().get(pk=group.pk)
        self.assertEqual(group.status, 'deleted')

    def test_no(self):
        """Group should not be deleted if the answer is no."""
        group = Group.objects.create(name='no')
        form = forms.GroupDeleteForm({'are_you_sure': 'no'})
        form.group = group
        self.assertTrue(form.is_valid())
        form.save()
        group = Group.objects.get(pk=group.pk)
        self.assertEqual(group.status, 'active')
