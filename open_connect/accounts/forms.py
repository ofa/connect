"""Forms for accounts app."""
# pylint: disable=no-init,no-self-use

from django import forms
from django.contrib.admin import widgets
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.timezone import now
from email.utils import formataddr

from open_connect.accounts.models import User, Invite
from open_connect.mailer.utils import clean_addresses
from open_connect.media.models import Image
from open_connect.groups.models import Group
from open_connect.connectmessages.models import Thread
from open_connect.connect_core.utils.mixins import SanitizeHTMLMixin


YES_NO_CHOICES = (('no', 'No'), ('yes', 'Yes'))


class UserImageForm(forms.ModelForm):
    """Form for GroupImage model."""
    image = forms.ImageField(required=False)

    class Meta(object):
        """Meta options."""
        model = Image
        fields = ['image']


class UserForm(SanitizeHTMLMixin, forms.ModelForm):
    """Form for creating/editing a user."""
    class Meta(object):
        """Meta options for UserForm."""
        model = User
        fields = [
            'first_name', 'last_name', 'biography', 'timezone',
            'facebook_url', 'twitter_handle', 'website_url',
            'group_notification_period', 'show_groups_on_profile',
            'receive_group_join_notifications', 'is_staff'
        ]

    def clean_biography(self):
        """Strip invalid html from biography field."""
        return self.sanitize_html(self.cleaned_data['biography'])


class UserAdminForm(forms.ModelForm):
    """Form for administering a User in the Django admin"""
    class Meta(object):
        """Meta options for the User Admin Form"""
        model = User
        exclude = []

    def __init__(self, *args, **kwargs):
        """Initialize the User Admin Form"""
        super(UserAdminForm, self).__init__(*args, **kwargs)


class TermsAndConductAcceptForm(forms.Form):
    """Form for accepting terms and conduct agreements."""
    accept_tos = forms.BooleanField(
        required=True,
        widget=forms.HiddenInput(),
        label=u'I agree to the Connect Terms of Service.'
    )
    accept_ucoc = forms.BooleanField(
        required=True,
        widget=forms.HiddenInput(),
        label=u'I agree to the Connect User Code of Conduct.'
    )
    next = forms.CharField(widget=forms.HiddenInput())

    def save(self, user_id):
        """Save the form."""
        user = User.objects.get(pk=user_id)
        user.tos_accepted_at = now()
        user.ucoc_accepted_at = now()
        user.save()
        return user


class InviteForm(forms.Form):
    """Form for inviting a user."""
    emails = forms.CharField(
        widget=forms.Textarea(),
        help_text='Use a comma to separate multiple addresses.'
    )
    is_staff = forms.BooleanField(required=False)
    is_superuser = forms.BooleanField(required=False)
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(),
        required=False
    )

    def clean_emails(self):
        """Clean up email field to only include symantically valid addresses"""
        emails = clean_addresses(self.data['emails'])

        if not len(emails):
            raise ValidationError('No Valid Addresses Found')

        email_string = [formataddr(entry) for entry in emails]

        return email_string

    def save(self):
        """Save the form."""
        is_staff = self.cleaned_data.get('is_staff', False)
        is_superuser = self.cleaned_data.get('is_superuser', False)
        groups = self.cleaned_data['groups']
        created_by = self.created_by
        invites = []
        for email in self.cleaned_data['emails']:
            invite, created = Invite.objects.get_or_create(
                email=email,
                defaults={
                    'is_staff': is_staff,
                    'is_superuser': is_superuser,
                    'created_by': created_by
                }
            )
            invite.send_invite(sender_id=self.created_by.pk)
            if created:
                # pylint: disable=expression-not-assigned
                [invite.groups.add(group) for group in groups]
                invites.append(invite)
        return invites


class BanUserForm(forms.Form):
    """Form for banning a user."""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.HiddenInput()
    )
    confirm = forms.BooleanField(
        label='Are you sure you want to ban this user?',
        required=False
    )

    def save(self):
        """Save the form result."""
        if not self.cleaned_data['confirm']:
            return
        user = self.cleaned_data['user']
        most_recent_threads = Thread.objects.filter(
            latest_message__sender=user,
        ).exclude(first_message__sender=user)
        for thread in most_recent_threads:
            try:
                latest_message = thread.message_set.exclude(
                    sender=user).filter(status='approved').latest('created_at')
            except ObjectDoesNotExist:
                continue
            thread.latest_message = latest_message
            thread.save()

        User.objects.filter(
            pk=user.pk).update(is_banned=True)


class UnBanUserForm(forms.Form):
    """Form for unbanning a user."""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.HiddenInput()
    )
    confirm = forms.BooleanField(
        label='Are you sure you want to unban this user?',
        required=False
    )

    def save(self):
        """Save the form result."""
        if not self.cleaned_data['confirm']:
            return

        user = self.cleaned_data['user']
        threads = Thread.objects.filter(
            message__sender=user, message__status='approved'
        )
        for thread in threads:
            latest_message = thread.message_set.latest('created_at')
            if thread.latest_message != latest_message:
                thread.latest_message = latest_message
                thread.save()

        User.objects.filter(
            pk=user.pk).update(is_banned=False)


class BecomeUserForm(forms.Form):
    """Form to become another user."""
    user_to_become = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.HiddenInput()
    )


class InviteEntryForm(forms.Form):
    """Form for consuming an invite."""
    invite_code = forms.CharField(max_length=32)

    def clean_invite_code(self):
        """Verify the invite code and return the invite object."""
        try:
            invite = Invite.objects.get(
                code=self.cleaned_data['invite_code'],
                consumed_at__isnull=True
            )
        except Invite.DoesNotExist:
            raise ValidationError('Invalid invite code')
        return invite

    def save(self):
        """Consume the invite and update the user."""
        self.cleaned_data['invite_code'].use_invite(self.user_id)


class AssignToPermGroupForm(forms.Form):
    """Form for adding users to a permission group in admin."""
    permission_group = forms.ModelChoiceField(
        queryset=AuthGroup.objects.filter(group__isnull=True),
        help_text='Select a permission group to assign users to'
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.MultipleHiddenInput()
    )

    def save(self):
        """Save the form."""
        group = self.cleaned_data['permission_group']
        for user in self.cleaned_data['users']:
            group.user_set.add(user)


class UserPermissionForm(forms.ModelForm):
    """Form for modifying user permissions."""
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        required=False,
        widget=widgets.FilteredSelectMultiple('Permission', False))

    class Meta(object):
        """Meta options."""
        model = User
        fields = ['user_permissions']
