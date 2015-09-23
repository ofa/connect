"""Views for the moderation app"""
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, UpdateView, View
from pure_pagination.mixins import PaginationMixin

from open_connect.groups.models import Group
from open_connect.moderation.forms import ModNotificationUpdateForm
from open_connect.moderation.models import Flag
from open_connect.moderation.utils import moderate_messages
from open_connect.connectmessages.models import Message, MESSAGE_STATUSES
from open_connect.connect_core.utils.mixins import (
    SortableListMixin,
    DateTimeRangeListMixin,
    PaginateByMixin
)
from open_connect.connect_core.utils.views import CommonViewMixin


POSSIBLE_ACTIONS = [statuspair[0] for statuspair in MESSAGE_STATUSES]


class ModeratorOnlyMixin(object):
    """Mixin that restricts the view to those who can moderate messages"""
    def dispatch(self, request, *args, **kwargs):
        """Override for the view's dispatch method"""
        if not request.user.can_moderate:
            raise Http404
        return super(ModeratorOnlyMixin, self).dispatch(
            request, *args, **kwargs)


class ModeratorView(
        PaginationMixin, ModeratorOnlyMixin, CommonViewMixin, ListView):
    """View that handles viewing messages to be moderated"""
    model = Message
    template_name = "moderation/messagelist.html"
    paginate_by = 20
    nav_active_item = 'Admin'
    dd_active_item = 'Message Moderation'

    def get_context_data(self, **kwargs):
        """Add additional context to the moderation page"""
        context = super(ModeratorView, self).get_context_data(**kwargs)
        group_id = self.kwargs.get('group')
        if group_id:
            context['group'] = get_object_or_404(Group, pk=group_id)

        return context

    def get_queryset(self):
        """Get the queryset for the page"""
        queryset = self.request.user.messages_to_moderate
        # Filter by group if group is in kwargs
        group = self.kwargs.get('group')
        if group:
            queryset = queryset.filter(thread__group_id=group)

        queryset = queryset.select_related(
            'thread', 'thread__group', 'thread__group__group', 'sender')

        return queryset


class SubmitView(ModeratorOnlyMixin, View):
    """View that processes"""
    http_method_names = [u'post']

    # pylint: disable=unused-argument, no-self-use
    def http_method_not_allowed(self, request, *args, **kwargs):
        """Redirect users who are not performing a POST request"""
        # Instead of just returning the standard "method not allowed" HTTP
        # status code, we can forward to the moderation admin
        return redirect(reverse('mod_admin'))

    # pylint: disable=no-self-use
    def get_success_url(self, request):
        """The url a user should be returned to if post was a success."""
        return request.POST.get('next', reverse('mod_admin'))

    # pylint: disable=unused-argument
    def post(self, request, **kwargs):
        """Process moderation changes."""
        change_count = 0
        actions = defaultdict(list)

        for message_string, action in request.POST.iteritems():
            if not message_string.startswith('message-'):
                continue
            message_id = message_string.split('-')[1]
            if message_id.isdigit() and action in POSSIBLE_ACTIONS:
                actions[action].append(message_id)

        if actions:
            change_count += moderate_messages(actions, request.user)

        if not change_count:
            messages.warning(request, 'No Messages Updated')
        else:
            pluralized_message = 'Messages' if change_count > 1 else 'Message'
            messages.success(
                request, "Updated %s %s" % (change_count, pluralized_message))

        cache.delete('%s_messages_to_mod' % self.request.user.pk)
        return redirect(self.get_success_url(request))


class ModerationFrequencyUpdateView(ModeratorOnlyMixin, UpdateView):
    """View for updating individual subscrptions for individual groups"""
    http_method_names = [u'post']
    model = get_user_model()
    form_class = ModNotificationUpdateForm
    success_url = reverse_lazy('user_profile')

    def get_object(self, queryset=None):
        """Get the User object to be modified"""
        return self.request.user

    def form_valid(self, form):
        """Method to handle a valid form"""
        form.save()
        messages.success(
            self.request, "Your moderation frequency has been set")
        return HttpResponseRedirect(self.get_success_url())


class FlagLogView(PaginationMixin, PaginateByMixin, DateTimeRangeListMixin,
                  SortableListMixin, CommonViewMixin, ModeratorOnlyMixin,
                  ListView):
    """List moderation actions."""
    model = Flag
    valid_order_by = [
        'moderation_action__messagemoderationaction__message__text',
        'moderation_action__messagemoderationaction__message__status',
        'flagged_by__first_name',
        'created_at',
        'moderation_action__moderator__first_name',
        'moderation_action__modified_at',
        'moderation_action__messagemoderationaction__newstatus'
    ]
    default_order_by = '-created_at'
    date_range_field = 'created_at'
    nav_active_item = 'Admin'
    dd_active_item = 'Flag Log'
    paginate_by = 25
    context_object_name = 'flags'

    def get_queryset(self):
        """Get the queryset for the Flag log"""
        queryset = super(FlagLogView, self).get_queryset()
        if not self.request.user.global_moderator:
            queryset = queryset.filter(
                message__thread__group__in=self.request.user.groups_moderating
            ).distinct()
        return queryset
