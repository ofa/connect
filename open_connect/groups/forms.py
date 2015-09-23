"""Group forms."""
# pylint: disable=no-init,too-few-public-methods

from autocomplete_light import MultipleChoiceWidget, ModelForm
from autocomplete_light.contrib.taggit_field import TaggitField, TaggitWidget
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from taggit.models import Tag
from open_connect.groups.tasks import add_user_to_group
from django.template.loader import render_to_string

from open_connect.groups.models import Group, GroupRequest, Category
from open_connect.groups.tasks import invite_users_to_group
from open_connect.media.models import Image
from open_connect.mailer.utils import clean_addresses
from open_connect.connect_core.utils.mixins import SanitizeHTMLMixin


class AuthGroupForm(forms.ModelForm):
    """Form for django.contrib.auth.models.Group."""
    class Meta(object):
        """Meta options."""
        model = AuthGroup
        fields = ['name']


class GroupImageForm(forms.ModelForm):
    """Form for GroupImage model."""
    image = forms.ImageField(label='Group Image', required=False)

    class Meta(object):
        """Meta options."""
        model = Image
        fields = ['image']


class GroupForm(SanitizeHTMLMixin, ModelForm):
    """Form for groups.models.Group."""
    category = forms.ModelChoiceField(
        label='Category', queryset=Category.objects.all())
    tags = TaggitField(
        widget=TaggitWidget(
            'TagAutocomplete', attrs={'placeholder': "type tags here"}),
        required=False)
    display_location = forms.CharField(
        label="Display Location",
        help_text=("Optionally enter the location you'd like displayed on the "
                   "group description page."),
        required=False,
        widget=forms.TextInput(
            attrs={'placeholder': "i.e. West Loop, Chicago, IL"})
    )
    whitelist_users = forms.ModelMultipleChoiceField(
        widget=MultipleChoiceWidget('UserAutocomplete'),
        help_text=u'These users will always be allowed to send to this group.',
        required=False,
        queryset=get_user_model().objects.all()
    )

    class Meta(object):
        """Meta options."""
        model = Group
        fields = ['category', 'description', 'tags', 'state',
                  'owners', 'whitelist_users', 'featured', 'private',
                  'published', 'moderated', 'member_list_published',
                  'display_location', 'latitude', 'longitude', 'radius']
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'radius': forms.HiddenInput(),
            'owners': MultipleChoiceWidget('UserAutocomplete'),
        }

    def clean_description(self):
        """Cleans the description field"""
        return self.sanitize_html(self.cleaned_data['description'])

    def clean_tags(self):
        """Clean the tags added into the form"""
        tags = self.cleaned_data['tags']
        invalid_tags = []
        valid_tags = Tag.objects.values_list('name', flat=True)
        for tag in tags:
            if tag not in valid_tags:
                invalid_tags.append(tag)
        if invalid_tags:
            self._errors['tags'] = self.error_class(
                ['These tags are invalid: %s.' % ', '.join(invalid_tags)]
            )
        return tags

    def save(self, *args, **kwargs):
        """Save the form"""
        self.instance.tos_accepted_at = now()
        result = super(GroupForm, self).save(*args, **kwargs)

        # For each group owner, added them to the group
        if self.instance.pk:
            for owner in self.cleaned_data['owners']:
                add_user_to_group.delay(owner.pk, self.instance.pk)

        return result


class GroupRequestForm(forms.Form):
    """Form for groups.models.GroupRequest."""
    open_requests = forms.ModelMultipleChoiceField(
        queryset=GroupRequest.objects.unapproved(),
        widget=forms.CheckboxSelectMultiple
    )
    action = forms.ChoiceField(
        choices=(('approve', 'Approve'), ('reject', 'Reject')),
        widget=forms.RadioSelect
    )

    def save(self, user):
        """Save the request."""
        open_requests = self.cleaned_data['open_requests']
        if self.cleaned_data['action'] == 'approve':
            for join_request in open_requests:
                subject = u"You've been added to {group}".format(
                    group=unicode(join_request.group))
                message = render_to_string(
                    'groups/notifications/added_to_group_notification.html',
                    {'group': join_request.group}
                )
                join_request.user.add_to_group(
                    join_request.group.pk, notification=[subject, message])
            open_requests.update(
                moderated_by=user, moderated_at=now(), approved=True
            )

        elif self.cleaned_data['action'] == 'reject':
            open_requests.update(
                moderated_by=user, moderated_at=now(), approved=False
            )


class GroupUserAddForm(forms.Form):
    """Form to quickly add a user to a form"""
    users = forms.MultipleChoiceField(
        widget=MultipleChoiceWidget('UserAutocomplete'))


class GroupInviteForm(forms.Form):
    """Form to invite others to groups by email"""
    emails = forms.CharField(
        widget=forms.Textarea(attrs={'style': "height: 300px; width: 100%;"}))
    verified = forms.BooleanField(widget=forms.HiddenInput, required=False)

    def clean_emails(self):
        """Clean up email field to only include symantically valid addresses"""
        addresses = clean_addresses(self.cleaned_data['emails'])

        if not addresses:
            raise ValidationError('No Valid Addresses Found')

        emails = ','.join([address[1] for address in addresses])
        return emails

    def save(self):
        """Process changes."""
        invite_users_to_group.delay(
            emails=self.cleaned_data['emails'],
            requester_id=self.user_id,
            group_id=self.group_id,
        )


class GroupDeleteForm(forms.Form):
    """Form for deleting a group."""
    are_you_sure = forms.ChoiceField(
        choices=(('no', 'No'), ('yes', 'Yes')),
        label=u'Are you sure you want to delete this group?'
    )

    def save(self):
        """Commit the changes."""
        # group will be set by the view
        if self.cleaned_data['are_you_sure'] == 'yes':
            self.group.delete()
        else:
            return self.group
