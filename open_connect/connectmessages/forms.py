"""Forms for connectmessages app."""
# pylint: disable=no-init
from django import forms
from django.contrib.auth import get_user_model

from open_connect.groups.models import Group
from open_connect.media.models import Image
from open_connect.connectmessages.models import Message, Thread
from open_connect.connect_core.utils.mixins import SanitizeHTMLMixin


USER_MODEL = get_user_model()


class BaseMessageForm(SanitizeHTMLMixin, forms.ModelForm):
    """Base form for creating messages."""
    images = forms.ModelMultipleChoiceField(
        queryset=Image.objects.all(),
        widget=forms.MultipleHiddenInput(),
        required=False
    )

    class Meta(object):
        """Meta options for BaseMessageForm."""
        model = Message
        # By default exclude no fields
        exclude = []

    def __init__(self, *args, **kwargs):
        self.instance = None
        super(BaseMessageForm, self).__init__(*args, **kwargs)

    def clean_text(self):
        """Strip unallowed html from message."""
        return self.sanitize_html(self.cleaned_data['text'])

    def save(self, commit=True):
        """Save a form and process image attachments."""
        self.instance = super(BaseMessageForm, self).save(commit)

        if commit:
            for image in self.cleaned_data['images']:
                self.instance.images.add(image)

        return self.instance


class NewMessageForm(BaseMessageForm):
    """Form for creating a new message."""
    subject = forms.CharField(required=True, max_length=255)

    def save(self, commit=True):
        """Save form and create message thread."""
        # If this is the commit pass, create a new thread
        if commit:
            group = self.cleaned_data.get('group', None)

            self.instance.thread = Thread.objects.create(
                subject=self.cleaned_data['subject'],
                group=group,
                thread_type=self.thread_type
            )

        return super(NewMessageForm, self).save(commit)


class MessageReplyForm(BaseMessageForm):
    """Form for replying to a message."""
    class Meta(BaseMessageForm.Meta):
        """Meta options for MessageReplyForm."""
        fields = ['text', 'images']


class GroupMessageForm(NewMessageForm):
    """Form for sending messages to multiple groups."""
    thread_type = 'group'
    # We set the queryset for this field in the view
    group = forms.ModelChoiceField(
        # This queryset should never be used
        # but we need it here to have our tests pass
        queryset=Group.objects.all()
    )

    class Meta(BaseMessageForm.Meta):
        """Meta options for GroupMessageForm."""
        fields = ['subject', 'text', 'group', 'images']


class SingleGroupMessageForm(GroupMessageForm):
    """Form for sending messages to one specific groups."""
    group = forms.ModelChoiceField(
        # This queryset should never be used
        # but we need it here to have our tests pass
        queryset=Group.objects.all(),
        widget=forms.HiddenInput()
    )


class DirectMessageForm(NewMessageForm):
    """Form for sending a message directly to users."""
    thread_type = 'direct'
    class Meta(BaseMessageForm.Meta):
        """Meta options for DirectMessageForm."""
        fields = ['subject', 'text', 'images']
