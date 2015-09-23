"""Views for the notifications app"""

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic import UpdateView
from django.http import Http404
from extra_views import ModelFormSetView

from open_connect.notifications.models import Subscription
from open_connect.notifications.forms import SubscriptionForm


class SubscriptionsUpdateView(ModelFormSetView):
    """View for updating overall subscriptions"""
    model = Subscription
    template_name = 'notifications/subscription_form.html'
    extra = 0
    can_delete = False
    form_class = SubscriptionForm

    def construct_formset(self):
        """Method to construct formsets in the SubscriptionUpdateView"""
        formset = super(SubscriptionsUpdateView, self).construct_formset()
        for form in formset:
            if hasattr(form, 'instance'):
                form.group_name = form.instance.group.group.name
        return formset

    def get_success_url(self):
        """Get the url to redirect a user to."""
        next_page = self.request.GET.get('next', None)
        if next_page:
            return next_page
        else:
            return reverse('update_subscriptions')

    def get_queryset(self):
        """
        Get the available queryset for this view.

        Specifically get all the subscriptions associated with the requesting
        user
        """
        return Subscription.objects.filter(user=self.request.user)

    def formset_invalid(self, formset):
        """Message to show and action to do when an invalid formset is sent"""
        messages.error(
            self.request, 'There was a problem updating your subscriptions.')
        return super(SubscriptionsUpdateView, self).formset_invalid(formset)

    def formset_valid(self, formset):
        """Message to show and action to do when a valid formset is sent"""
        formset.save()
        messages.success(self.request, 'Your subscriptions have been updated.')
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        """Return to the template the relevant context information"""
        context = super(
            SubscriptionsUpdateView, self).get_context_data(**kwargs)
        context['nav_active_item'] = self.request.user
        context['dd_active_item'] = 'Subscriptions'
        return context


class SubscriptionUpdateView(UpdateView):
    """View for updating individual subscrptions for individual groups"""
    model = Subscription
    form_class = SubscriptionForm

    def get_success_url(self):
        """Find the correct "next" url after a successful submission"""
        if 'return_url' in self.request.POST:
            return self.request.POST['return_url']
        return super(SubscriptionUpdateView, self).get_success_url()

    def get_object(self, queryset=None):
        """Get the specific subscription needed for the view"""
        return Subscription.objects.get(
            user=self.request.user, group=self.kwargs['group_id']
        )

    def form_valid(self, form):
        """Handle a valid form submission (save & return a message)"""
        form.save()
        messages.success(
            self.request, "Your subscription preference has been updated.")
        return HttpResponseRedirect(self.get_success_url())


class LoggedOutSubscriptionView(SubscriptionsUpdateView):
    """
    A version of Subscriptions Update View that does not require the user to
    be logged in to the site. This will be used in emails.

    Uses the user's private hash to identify the user.
    """

    def get_queryset(self):
        """Get the subscription for the user even if they're logged out"""
        user = get_object_or_404(get_user_model(), pk=self.kwargs['user_id'])

        # Check the provided key to the user's private hash
        if self.kwargs['key'] != user.private_hash:
            raise Http404
        return Subscription.objects.filter(user=user)
