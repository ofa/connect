"""Groups views."""
from collections import OrderedDict
from json import dumps
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import DetailView, ListView, FormView
from pure_pagination.mixins import PaginationMixin

from open_connect.connect_core.utils.views import CommonViewMixin
from open_connect.groups.forms import (
    GroupForm,
    AuthGroupForm,
    GroupRequestForm,
    GroupImageForm,
    GroupInviteForm,
    GroupUserAddForm,
    GroupDeleteForm
)
from open_connect.groups.models import Group, GroupRequest, Category
from open_connect.groups.tasks import add_user_to_group
from open_connect.media.models import Image
from open_connect.resources.models import Resource
from open_connect.notifications.forms import SubscriptionForm
from open_connect.notifications.models import Subscription
from open_connect.connect_core.utils.location import (
    get_coordinates
)
from open_connect.connect_core.utils.views import MultipleFormsView


LOGGER = logging.getLogger('groups.views')


class GroupCreateView(CommonViewMixin, MultipleFormsView):
    """View for creating a Group."""
    form_classes = OrderedDict({
        'authgroup_form': AuthGroupForm,
        'group_form': GroupForm,
        'image_form': GroupImageForm
    })
    template_name = 'groups/group_form.html'
    nav_active_item = 'Groups'

    def __init__(self):
        super(GroupCreateView, self).__init__()
        self.object = None

    def get_success_url(self):
        """URL to redirect to on success."""
        return reverse('group_details', args=[self.object.pk])

    def get_form_kwargs(self, form_class_name):
        """Add form name to form as the prefix."""
        kwargs = super(GroupCreateView, self).get_form_kwargs(form_class_name)
        kwargs['prefix'] = form_class_name
        return kwargs

    def form_valid(self, forms, all_cleaned_data):
        """Save a valid form and redirect the user."""
        if forms['group_form'].instance.pk:
            messages.success(
                self.request, 'You have successfully modified a group.')
            created = False
        else:
            messages.success(
                self.request, 'You have successfully created a group.')
            created = True
            forms['group_form'].instance.created_by = self.request.user
        # Save the django auth group
        auth_group = forms['authgroup_form'].save()

        # Save the image
        if forms['image_form'].cleaned_data['image']:
            forms['image_form'].instance.user = self.request.user
            image = forms['image_form'].save()
            forms['group_form'].instance.image = image

        forms['group_form'].instance.group = auth_group
        group = forms['group_form'].save()

        # Only add the user as owner and member if this is a new group
        if created:
            self.request.user.add_to_group(group.pk)
            group.owners.add(self.request.user)

        self.object = group
        return super(GroupCreateView, self).form_valid(forms, all_cleaned_data)

    def form_invalid(self, forms):
        """Method to display a message on invalid form submissions"""
        messages.warning(
            self.request,
            'Please check that required fields are filled out correctly.'
        )
        return super(GroupCreateView, self).form_invalid(forms)


class GroupUpdateView(GroupCreateView, CommonViewMixin):
    """View for updating a Group."""
    nav_active_item = 'Group'

    def __init__(self):
        super(GroupUpdateView, self).__init__()
        self._group = None

    def disallow_non_owners(self):
        """Only allow group owners and superusers to edit a group."""
        user = self.request.user
        if user.is_superuser or user.has_perm('groups.can_edit_any_group'):
            return
        if not user.has_perm('groups.change_group'):
            raise PermissionDenied
        if not self.group.owners.filter(pk=user.pk).exists():
            raise Http404

    def get(self, request, *args, **kwargs):
        """Call disallow_non_owners in get requests."""
        self.disallow_non_owners()
        response = super(GroupUpdateView, self).get(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        """Call disallow_non_owners in post requests."""
        self.disallow_non_owners()
        response = super(GroupUpdateView, self).post(request, *args, **kwargs)
        return response

    @property
    def group(self):
        """Cache the group object and return it."""
        if not self._group:
            self._group = Group.objects.get(pk=self.kwargs['pk'])
        return self._group

    def get_form_kwargs(self, form_class_name):
        """Bind the forms to the correct instances."""
        kwargs = super(GroupUpdateView, self).get_form_kwargs(form_class_name)
        if form_class_name == 'authgroup_form':
            kwargs['instance'] = self.group.group
        elif form_class_name == 'group_form':
            kwargs['instance'] = self.group
        return kwargs

    def get_context_data(self, **kwargs):
        """Add group to the view context."""
        context = super(GroupUpdateView, self).get_context_data(**kwargs)
        context['group'] = self.group
        return context


class GroupDetailView(CommonViewMixin, DetailView):
    """View for a group's detail."""
    model = Group
    nav_active_item = 'Groups'

    def get_context_data(self, **kwargs):
        """Add public threads to view context"""
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        if self.object in self.request.user.groups_joined:
            threads = self.object.public_threads_by_user(
                self.request.user
            ).select_related(
                'first_message', 'latest_message', 'first_message__sender',
                'latest_message__sender'
            ).order_by('-latest_message__created_at')[:3]
        else:
            threads = self.object.public_threads()[:3]

        context['resources'] = Resource.objects.filter(
            groups__pk=self.object.pk)

        for thread in threads:
            thread.messages = thread.messages_for_user(self.request.user)

        context['public_threads'] = threads

        try:
            subscription = Subscription.objects.get(
                user=self.request.user, group=self.object)
        except Subscription.DoesNotExist:
            subscription = None
        if subscription:
            context['subscription_form'] = SubscriptionForm(
                instance=subscription)
        else:
            context['subscription_form'] = None

        context['useradd_form'] = GroupUserAddForm()
        context['group_images'] = self.object.images(user=self.request.user)
        context['group_owners'] = self.object.owners.select_related(
            'image').all()

        return context


class GroupListView(CommonViewMixin, ListView):
    """View for listing groups."""
    model = Group
    located = False
    template_name = "groups/group_list.html"
    context_object_name = 'groups'
    nav_active_item = 'Groups'
    dd_active_item = 'My Groups'

    def get_queryset(self):
        """Modify queryset if there are search params in the request."""
        location = self.request.GET.get('location')
        query = self.request.GET.get('q')
        coords = None

        if location:
            coords = get_coordinates(location)

        if coords:
            self.located = True

        queryset = Group.objects.search(
            search=query, location=coords)

        return queryset

    def get_context_data(self, **kwargs):
        """Group list view context object populator"""
        context = super(GroupListView, self).get_context_data(**kwargs)

        context['q'] = self.request.GET.get('q', '')
        context['categories'] = Category.objects.filter(
            # Because we use `queryset.extra(select=,where=)` and the `where=`
            # explictly mentions "group_groups" we cannot include that query as
            # part of the query that gets our categories.
            pk__in=list(self.object_list.values_list(
                'category_id', flat=True)))
        context['location'] = self.request.GET.get('location')
        context['located'] = self.located

        if self.request.user.is_authenticated():
            user = self.request.user
            requested_ids = GroupRequest.objects.filter(
                user=user, approved__isnull=True).values_list(
                    'group_id', flat=True)
            subscribed_ids = user.groups_joined.values_list('pk', flat=True)
            moderating_ids = user.groups_moderating.values_list(
                'id', flat=True)
        else:
            requested_ids = []
            subscribed_ids = []
            moderating_ids = []

        context['requested_ids'] = requested_ids
        context['subscribed_ids'] = subscribed_ids
        context['moderating_ids'] = moderating_ids

        return context


class MyGroupsView(GroupListView):
    """View for listing groups that a user belongs to."""
    model = Group
    template_name = "groups/my_groups_list.html"

    def get_queryset(self):
        """Update queryset to include only groups the user belongs to."""
        return Group.objects.filter(group__user=self.request.user)


def handle_group_subscription(request, action):
    """Handles a subscription request."""
    group_id = request.POST.get('group_id', -1)
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        response = {
            'success': False,
            'message': "Requested group doesn't exist.",
            'group_id': group_id
        }
    else:
        response = {
            'success': True,
            'group_id': group.pk
        }
        if action == 'subscribe':
            if group.private:
                request.user.request_to_join_group(group)
                response['message'] = (
                    'Your request to join %s has been received.' % group)
            else:
                request.user.add_to_group(group.pk, immediate=True)
                response['message'] = (
                    '<div>Successfully joined %s.</div>' % group)
        elif action == 'unsubscribe':
            request.user.remove_from_group(group)
            response['message'] = 'Successfully unsubscribed from %s.' % group
    return HttpResponse(dumps(response))


def group_subscribe_view(request):
    """View for subscribing to a group."""
    return handle_group_subscription(request, 'subscribe')


def group_unsubscribe_view(request):
    """View for unsubscribing from a group."""
    return handle_group_subscription(request, 'unsubscribe')


class GroupRequestUpdateView(CommonViewMixin, FormView):
    """View for updating a GroupRequest."""
    form_class = GroupRequestForm
    template_name = 'groups/grouprequest_form.html'
    nav_active_item = 'Groups'

    def get_form(self, form_class):
        """Only show requests for groups a user is owner of."""
        form = super(GroupRequestUpdateView, self).get_form(form_class)
        if not self.request.user.is_superuser:
            form.fields['open_requests'].queryset = (
                form.fields['open_requests'].queryset.filter(
                    group__owners=self.request.user)
            )
        return form

    def get_context_data(self, **kwargs):
        """Add number of requests to the view context."""
        context = super(GroupRequestUpdateView, self).get_context_data(**kwargs)
        if 'form' in kwargs:
            context['request_count'] = (
                kwargs['form'].fields['open_requests'].queryset.count())
        return context

    # pylint: disable=no-self-use
    def get_success_url(self):
        """URL to redirect to on success."""
        return reverse('moderate_requests')

    def form_valid(self, form):
        """Save the form and redirect the user."""
        form.save(self.request.user)
        cache.delete('%s_groups_to_mod' % self.request.user.pk)
        return super(GroupRequestUpdateView, self).form_valid(form)


class GroupImagesView(ListView):
    """View for listing GroupImages."""
    model = Image
    template_name = 'groups/group_images.html'
    context_object_name = 'images'

    def get_queryset(self):
        """Update queryset to include images a user should have access to."""
        group_id = self.kwargs.get('group_id')
        queryset = Image.popular.with_user(
            self.request.user
        ).filter(
            message__thread__group__pk=group_id
        )
        return queryset

    def get_context_data(self, **kwargs):
        """Add the group to the context."""
        context = super(GroupImagesView, self).get_context_data(**kwargs)
        context['group'] = get_object_or_404(
            Group, pk=self.kwargs.get('group_id'))
        return context


class GroupMemberListView(PaginationMixin, ListView):
    """View for listing of members of a group."""
    model = get_user_model()
    template_name = 'groups/group_member_list.html'
    context_object_name = 'group_members'

    def get_queryset(self):
        """Only get members of the current group.

        Group must have member_list_published or the user has to be superuser
        or a group owner.
        """
        group = Group.objects.get(pk=self.kwargs['pk'])
        user = self.request.user
        if (group.member_list_published
                or user.is_superuser
                or group.owners.filter(pk=user.pk).exists()):
            queryset = super(GroupMemberListView, self).get_queryset().filter(
                groups__group=group
            ).exclude(
                pk__in=group.owners.all().only('pk')).order_by('first_name')
            if self.request.GET.get('q'):
                query = self.request.GET['q']
                queryset = queryset.filter(
                    Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(email__icontains=query)
                )
            queryset = queryset.select_related('image')
            return queryset
        else:
            raise Http404

    def get_context_data(self, **kwargs):
        """Add the group to the context."""
        context = super(GroupMemberListView, self).get_context_data(**kwargs)
        group = get_object_or_404(Group, pk=self.kwargs.get('pk'))
        context['group'] = group
        context['q'] = self.request.GET.get('q', '')
        context['user_is_owner'] = self.request.user.groups_moderating.filter(
            pk=self.kwargs.get('pk'))
        context['group_owners'] = group.owners.all().order_by('first_name')
        return context


@require_http_methods(["POST"])
def group_quick_user_add(request, group_id):
    """A view that takes a list of user IDs and adds them to groups"""
    group = get_object_or_404(Group, pk=group_id)
    # If there is no users in the POST or the users post is empty, bail out
    if not 'users' in request.POST or not request.POST['users']:
        messages.warning(request, 'No Users Entered')
    else:
        subject = 'You\'ve been added to {group}'.format(group=str(group))
        message = render_to_string(
            'groups/notifications/added_to_group_notification.html',
            {'group': group}
        )
        total_processed = 0
        for user_id in request.POST.getlist('users'):
            if user_id.isdigit():
                add_user_to_group.delay(
                    user_id, group_id, notification=(subject, message))
                total_processed += 1
        plural = '' if total_processed == 1 else 's'
        messages.success(request, '{total} User{plural} Added'.format(
            total=total_processed, plural=plural))

    return redirect(reverse('group_details', args=[group_id]))


class GroupMemberInviteView(CommonViewMixin, FormView):
    """View to invite people to groups"""
    form_class = GroupInviteForm
    template_name = 'groups/group_invite.html'
    nav_active_item = "Groups"

    def get_success_url(self):
        """URL to redirect to on success."""
        return reverse('group_details', args=[self.kwargs['pk']])

    def form_valid(self, form):
        """Handle a valid form."""
        data = form.cleaned_data
        if not data['verified']:
            data['verified'] = True
            new_form = GroupInviteForm(data)

            # Grab the cleaned addresses then match them to the user list
            emails = [email.strip() for email in data['emails'].split(',')]
            existing_users = get_user_model().objects.filter(email__in=emails)
            existing_emails = existing_users.values_list('email', flat=True)
            new_users = set(emails).difference(set(existing_emails))

            return self.render_to_response(self.get_context_data(
                form=new_form,
                data=data,
                existing=existing_users,
                new=new_users,
                verify=True
            ))
        else:
            form.group_id = self.kwargs['pk']
            form.user_id = self.request.user.pk
            form.save()
            messages.info(
                self.request, u"We're processing your invite request.")

        return super(GroupMemberInviteView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        """Add the group to the context."""
        context = super(GroupMemberInviteView, self).get_context_data(**kwargs)
        context['group'] = get_object_or_404(Group, pk=self.kwargs.get('pk'))
        return context


class GroupDeleteView(FormView):
    """View for "deleting" a group."""
    form_class = GroupDeleteForm
    template_name = 'groups/group_delete.html'

    def get_context_data(self, **kwargs):
        """Add the group to the context."""
        context = super(GroupDeleteView, self).get_context_data(**kwargs)
        context['group'] = get_object_or_404(Group, pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        """Delete the group."""
        form.group = get_object_or_404(Group, pk=self.kwargs['pk'])
        result = form.save()
        if result:
            messages.info(self.request, u'The group has not been deleted.')
            return HttpResponseRedirect(
                reverse('group_details', kwargs={'pk': self.kwargs['pk']}))
        else:
            messages.info(self.request, u'The group has been deleted.')
            return HttpResponseRedirect(reverse('groups'))


@require_POST
def remove_user_from_group_view(request, user_uuid, group_id):
    """JSON endpoint for removing a user from a group."""
    if Group.objects.filter(owners__pk=request.user.pk, pk=group_id).exists():
        user = get_user_model().objects.get(uuid=user_uuid)
        user.remove_from_group(group_id)
        return HttpResponse(
            dumps({
                'success': True,
                'errors': '',
            }),
            content_type='application/json'
        )
    else:
        return HttpResponse(
            dumps({
                'success': False,
                'error': "User is not an owner of this group."
            }),
            content_type='application/json'
        )
