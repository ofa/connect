"""Forms for the moderation app"""
from django import forms

from django.contrib.auth import get_user_model


class ModNotificationUpdateForm(forms.ModelForm):
    """Form for creating/editing subscriptions."""
    class Meta(object):
        """SubscriptionForm meta options."""
        model = get_user_model()
        fields = ['moderator_notification_period']
        widgets = {
            'moderator_notification_period': forms.widgets.RadioSelect()
        }
