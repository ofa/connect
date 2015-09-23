"""Views for connectmessages."""
from datetime import datetime
import time

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponse, HttpResponseRedirect, Http404
)
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.utils.timezone import (
    get_current_timezone,
    make_aware,
    get_current_timezone_name
)
import simplejson as json

from open_connect.accounts.models import PermissionDeniedError
from open_connect.groups.models import Group
from open_connect.notifications.tasks import create_recipient_notifications
from open_connect.connectmessages.forms import (
    MessageReplyForm, GroupMessageForm, DirectMessageForm,
    SingleGroupMessageForm)
from open_connect.connectmessages.models import (
    Message, UserThread, Thread, ImageAttachment
)
from open_connect.connect_core.utils.mixins import SortableListMixin
from open_connect.connect_core.utils.stringhelp import str_to_bool
from open_connect.connect_core.utils.views import (
    CommonViewMixin, JSONResponseMixin
)


class BaseThreadListView(SortableListMixin, ListView):
    """Mixin for views that display threads of messages"""
    model = Thread
    paginate_by = 20
    valid_order_by = ['created_at', 'latest_message__created_at']
    default_order_by = '-latest_message__created_at'

    def get_queryset(self):
        """Get only threads for a user, and get some related data in query."""
        get_data = self.request.GET
        threads = self.model.public.by_user(self.request.user)

        # Run the queryset through `SortableListMixin` to allow ordering
        threads = self.order_queryset(threads)

        if 'status' in get_data:
            threads = threads.extra(
                where=[
                    "connectmessages_userthread.status = %s"
                ],
                params=(get_data['status'],)
            )

        # Filter by group(s)
        if 'group' in get_data:
            group_ids = [
                int(pk) for pk in get_data.get('group', '').split(u',')
                if pk.isdigit() and int(pk) >= 0
            ]
            threads = threads.filter(group__pk__in=group_ids)

        # Check to see if the GET variable `since` exists and
        # confirm it's an interger
        if get_data.get('since', '').isdigit():
            threads = threads.filter(
                modified_at__gte=make_aware(
                    datetime.fromtimestamp(
                        int(get_data['since'])),
                    get_current_timezone()
                )
            )

        # Allow to query by ID number
        if 'id' in get_data:
            # Generate a list of positive integer from thread string
            threads_ids = [
                int(pk) for pk in get_data.get('id', '').split(u',')
                if pk.isdigit() and int(pk) >= 0
            ]
            threads = threads.filter(pk__in=threads_ids)

        if 'read' in get_data:
            threads = threads.extra(
                where=[
                    "connectmessages_userthread.read = %s"
                ],
                params=(str_to_bool(get_data['read']),)
            )

        return threads

    def get_serialized_threads(self, threads):
        """Get a serialized list of threads"""
        timezone = self.request.user.timezone
        thread_list = [
            thread.serializable(timezone) for thread in threads
        ]

        return thread_list

    def get_js_context_data(self):
        """Get context necessary for client-side functionality"""
        js_context = {
            'current_time': int(time.time()),
            'alerts': self.request.user.get_moderation_tasks()
        }
        return js_context


class InboxView(BaseThreadListView):
    """Inbox/messages/thread list, whatever you like to call it."""
    template_name = 'connectmessages/thread_list.html'

    def get_context_data(self, **kwargs):
        """Add necessary information to the context"""
        context = super(InboxView, self).get_context_data(**kwargs)

        #serialized_threads = None

        # We're provided a paginator as part of our ListView parent and as
        # part of generating that paginator a `.count()` is run against our
        # queryset. This is a quick way to get our count without another query
        # even if we don't need the paginator
        thread_count = context['paginator'].count

        # Generate the context variable to be passed to the backbone models
        js_context = self.get_js_context_data()
        js_context['total_threads'] = thread_count
        context['js_context'] = json.dumps(js_context)
        return context


class ThreadJSONListView(JSONResponseMixin, BaseThreadListView):
    """Get a list of threads as JSON."""
    # pylint: disable=unused-argument
    def post(self, request, **kwargs):
        """Handle POST requests which change threads"""
        post_data = self.request.POST

        threads = self.get_queryset()

        # If there are no threads in this queryset, throw a 404
        if threads.count() == 0:
            raise Http404

        userthreads = UserThread.objects.filter(
            user=self.request.user, thread__pk__in=threads)

        changes = {}

        # Allow changing the `read` status of the thread
        if 'read' in post_data:
            if str_to_bool(post_data['read']):
                changes['last_read_at'] = now()
                changes['read'] = True
            else:
                changes['last_read_at'] = None
                changes['read'] = False

        if 'status' in post_data:
            if post_data['status'] == 'archived':
                changes['status'] = 'archived'
            elif post_data['status'] == 'active':
                changes['status'] = 'active'

        if 'subscribed' in post_data:
            if str_to_bool(post_data['subscribed']):
                changes['subscribed_email'] = True
            else:
                changes['subscribed_email'] = False

        if len(changes) > 0:
            rows = userthreads.update(**changes)
            status_code = 200
            success = True
        else:
            # If no changes were made, return a 400 status code
            rows = 0
            status_code = 400
            success = False

        return HttpResponse(
            json.dumps({'success': success, 'rows': rows}),
            content_type='application/json',
            status=status_code
        )


    def get_context_data(self, **kwargs):
        """Generate the JSON context"""
        context = self.get_js_context_data()
        queryset = self.get_queryset()

        # Paginate the queryset
        page_size = self.get_paginate_by(queryset)
        paginator, page, threads, has_other_pages = self.paginate_queryset(
            queryset, page_size)

        # Serialize the threads returned by the paginator
        context['threads'] = self.get_serialized_threads(threads)

        context['paginator'] = {}

        context['paginator']['total_threads'] = paginator.count
        context['paginator']['page_number'] = page.number
        context['paginator']['total_pages'] = paginator.num_pages
        context['paginator']['has_other_pages'] = has_other_pages

        return context


class ThreadJSONDetailView(JSONResponseMixin, DetailView):
    """Display a thread of messages."""
    def get_object(self):
        """Get the thread object"""
        try:
            thread = Thread.public.get_by_user(
                thread_id=self.kwargs['pk'],
                user=self.request.user
            )
        except ObjectDoesNotExist:
            raise Http404
        return thread

    # pylint: disable=unused-argument
    def get_context_data(self, **kwargs):
        """Update view context."""
        context = {}

        thread = self.object
        try:
            user_thread = UserThread.objects.get(
                user=self.request.user, thread=thread)
        except ObjectDoesNotExist:
            pass
        else:
            thread.userthread_status = user_thread.status
            thread.last_read_at = user_thread.last_read_at
            thread.read = user_thread.read

        timezone = get_current_timezone_name()
        context['connectmessages'] = [
            message.serializable(timezone=timezone) for message
            in thread.messages_for_user(self.request.user)
        ]
        context['thread'] = thread.serializable(timezone=timezone)

        # Check to see if the user has seen this message. If not, update the
        # UserThread to mark the thread as "read"
        UserThread.objects.filter(
            thread=thread, user=self.request.user
        ).update(read=True, last_read_at=now())

        return context


class MessageCreateView(CreateView):
    """View for creating a new message."""
    model = Message
    form_class = GroupMessageForm

    def get_template_names(self):
        """Use the right template."""
        embed = self.request.GET.get('embed', 'no') == 'yes'
        if embed:
            return 'connectmessages/message_form_embedded.html'
        else:
            return 'connectmessages/message_form.html'

    # pylint: disable=no-self-use
    def get_success_url(self):
        """The url to redirect to if creation is successful."""
        return reverse('threads')

    def get_form(self, form_class):
        """Get an instance of the form and add the sender_id."""
        form = super(MessageCreateView, self).get_form(form_class)
        form.instance.sender_id = self.request.user.pk
        return form

    def form_valid(self, form):
        """Process a valid form and redirect the user."""
        form.instance.sender_id = self.request.user.pk
        headers = self.request.META
        # Could sometimes be a list of addresses in X_FORWARDED_FOR.
        ip_addresses = headers.get(
            'HTTP_X_FORWARDED_FOR', headers.get('REMOTE_ADDR')).split(',')
        if ip_addresses:
            form.instance.ip_address = ip_addresses[0]
        form.instance.user_agent = headers.get('HTTP_USER_AGENT')

        # pylint: disable=attribute-defined-outside-init
        self.object = form.save()
        if self.object.status == 'approved':
            messages.success(self.request, u'Your message has been sent.')
        else:
            messages.success(
                self.request,
                u'Your message has been sent and is pending approval.'
            )
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """Create a warning message when a form is marked invalid"""
        messages.warning(
            self.request,
            'Please check that required fields are filled out correctly.'
        )
        return super(MessageCreateView, self).form_invalid(form)


class GroupMessageCreateView(CommonViewMixin, MessageCreateView):
    """View for creating a new message to a group."""
    nav_active_item = "Inbox"

    def get_form(self, form_class):
        """Get an instance of the form and limit groups."""
        form = super(GroupMessageCreateView, self).get_form(form_class)

        # Users should only see groups they're authorized to view
        form.fields['group'].queryset = self.request.user.messagable_groups
        return form


class SingleGroupMessageCreateView(CommonViewMixin, MessageCreateView):
    """View for creating a new message to a specific group."""
    form_class = SingleGroupMessageForm

    def dispatch(self, *args, **kwargs):
        """Dispatch the request"""
        # pylint: disable=attribute-defined-outside-init
        self.group = get_object_or_404(
            Group, pk=kwargs['group_id'])
        try:
            self.request.user.can_send_to_group(self.group)
        except PermissionDeniedError:
            messages.warning(
                self.request,
                "You don't have permission to post to this group."
            )
            return HttpResponseRedirect(reverse('threads'))

        return super(
            SingleGroupMessageCreateView, self).dispatch(*args, **kwargs)

    def get_initial(self):
        """Get the initial data for the form. In this case the group."""
        initial = super(SingleGroupMessageCreateView, self).get_initial()
        initial['group'] = self.group
        return initial

    def get_context_data(self, **kwargs):
        """Get the context for the view."""
        context = super(
            SingleGroupMessageCreateView, self).get_context_data(**kwargs)
        context['group'] = self.group
        return context


# pylint: disable=attribute-defined-outside-init
class DirectMessageCreateView(MessageCreateView):
    """View for creating a new message to another user."""
    model = Message
    form_class = DirectMessageForm

    def dispatch(self, request, *args, **kwargs):
        """Dispatch the request"""
        self.recipient = get_object_or_404(
            get_user_model(), uuid=kwargs['user_uuid'])

        if not request.user.can_direct_message_user(self.recipient):
            messages.warning(
                request,
                "You don't have permission to direct message "
                "{recipient}.".format(recipient=self.recipient)
            )
            return HttpResponseRedirect(reverse('threads'))

        return super(DirectMessageCreateView, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Get the context for the view."""
        context = super(
            DirectMessageCreateView, self).get_context_data(**kwargs)
        context['recipient'] = self.recipient
        context['nav_active_item'] = 'Threads'
        return context

    def form_valid(self, form):
        """Handle a valid form"""
        response = super(DirectMessageCreateView, self).form_valid(form)
        self.object.thread.add_user_to_thread(self.recipient)
        # Sender shouldn't see their own messages as unread
        UserThread.objects.filter(
            thread_id=self.object.thread.pk, user=self.request.user
        ).update(read=True, last_read_at=now())
        create_recipient_notifications.delay(self.object.pk)
        return response


class MessageReplyView(MessageCreateView):
    """View for replying to a message"""
    form_class = MessageReplyForm

    def dispatch(self, *args, **kwargs):
        """Dispatch the request"""
        # Get the thread to be replied to
        self.thread = get_object_or_404(
            Thread, pk=kwargs['thread_id'])

        # If the thread is closed, redirect the user to the thread list and
        # with a warning message saying that replies to a closed thread is
        # not an allowed action
        if self.thread.closed:
            messages.warning(
                self.request,
                '%s is closed and cannot be replied to' % self.thread
            )
            return HttpResponseRedirect(reverse('threads'))

        # If user doesn't have permission to reply to the thread
        try:
            self.request.user.can_send_to_group(self.thread.group)
        except PermissionDeniedError:
            messages.warning(
                self.request,
                "You don't have permission to post to this group."
            )
            return HttpResponseRedirect(reverse('threads'))

        # We actually call the super() of the parent.
        # pylint: disable=bad-super-call
        return super(MessageCreateView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        """Get the context for the view."""
        context = super(MessageReplyView, self).get_context_data(**kwargs)
        context['thread'] = self.thread
        context['connectmessages'] = self.thread.messages_for_user(
            self.request.user)
        context['nav_active_item'] = 'Threads'
        context['hide_message_controls'] = True
        return context

    def form_valid(self, form):
        """Process a valid form."""
        form.instance.thread = self.thread
        return super(MessageReplyView, self).form_valid(form)


class DirectMessageReplyView(MessageReplyView):
    """View for replying to a message"""
    form_class = MessageReplyForm

    def get_context_data(self, **kwargs):
        """Get the context for the view."""
        context = super(
            DirectMessageReplyView, self).get_context_data(**kwargs)
        context['recipient'] = self.thread.recipients.exclude(
            pk=self.request.user.pk).get()
        return context

    def form_valid(self, form):
        result = super(DirectMessageReplyView, self).form_valid(form)
        create_recipient_notifications.delay(self.object.pk)
        return result


# pylint: disable=unused-argument
def image_view(request, image_id):
    """View for listing images. Used by redactor js rte."""
    image = ImageAttachment.objects.get(pk=image_id)
    image.view_count += 1
    image.save()
    return HttpResponseRedirect(image.image.url)


# pylint: disable=unused-argument
@require_POST
def thread_unsubscribe_view(request, thread_id):
    """Unsubscribe from receiving email notifications to a thread"""
    userthread = get_object_or_404(
        UserThread, thread_id=thread_id, user=request.user)
    userthread.subscribed_email = False
    messages.success(request, 'You have unsubscribed from this thread.')
    userthread.save(update_fields=["subscribed_email"])
    return HttpResponse(
        json.dumps({'success': True, 'id': userthread.thread.pk}),
        content_type='application/json'
    )


@require_POST
def message_flag_view(request, message_id):
    """Flag a message for moderator approval."""
    message = get_object_or_404(Message, pk=message_id)
    message.flag(flagged_by=request.user)
    response = json.dumps({
        'success': True,
        'errors': [],
        'message_id': message_id,
        'message': 'You have successfully flagged a message.'
    })
    return HttpResponse(response, content_type='application/json')


def unread_message_count_view(request):
    """Returns json with count of unread messages."""
    unread_count = UserThread.objects.filter(
        user=request.user, thread__status='active'
    ).exclude(read=True).extra(
        where=[
            'connectmessages_message.thread_id ='
            ' connectmessages_userthread.thread_id',
            "connectmessages_message.status = 'approved'",
            'connectmessages_userthread.last_read_at IS NULL OR'
            ' connectmessages_message.created_at >'
            ' connectmessages_userthread.last_read_at'
        ],
        tables=['connectmessages_message']
    ).count()
    moderation_tasks = request.user.get_moderation_tasks()
    unread_count = (
        unread_count
        + moderation_tasks['groups_to_mod']
        + moderation_tasks['messages_to_mod']
    )
    response = json.dumps(
        {'success': True, 'errors': [], 'unread_count': unread_count})
    return HttpResponse(response, content_type='application/json')
