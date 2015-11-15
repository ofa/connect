"""Forms for the notifications app."""
# pylint: disable=no-init,unused-import

from django import forms
from django.forms import widgets
from django.forms.models import modelformset_factory

from open_connect.notifications.models import Subscription


class SubscriptionForm(forms.ModelForm):
    """Form for creating/editing subscriptions."""
    class Meta(object):
        """SubscriptionForm meta options."""
        model = Subscription
        widgets = {
            'period': widgets.RadioSelect()
        }
        exclude = ['user', 'group']


def get_subscription_formset(user):
    """Create a subscription formset for a user."""
    # pylint: disable=invalid-name
    SubscriptionModelFormSet = modelformset_factory(
        Subscription, form=SubscriptionForm, extra=0, can_delete=False)
    subscription_formset = SubscriptionModelFormSet(
        queryset=Subscription.objects.filter(
            user=user).select_related('group__group', 'group__category'))
    for form in subscription_formset:
        if hasattr(form, 'instance'):
            form.group_name = form.instance.group.group.name
    return subscription_formset
