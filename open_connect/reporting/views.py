"""Views for generating reports."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.http import HttpResponse
from django.views.generic import ListView
from pure_pagination import PaginationMixin
from tablib import Dataset

from open_connect.accounts.views import SuppressSystemUserMixin
from open_connect.groups.models import Group
from open_connect.groups.utils import (
    groups_string, groups_tags_string, groups_categories_string
)
from open_connect.connect_core.utils.mixins import (
    SortableListMixin,
    DateTimeRangeListMixin,
    PaginateByMixin
)
from open_connect.connect_core.utils.views import CommonViewMixin


User = get_user_model()


class UserReportListView(
        SuppressSystemUserMixin, PaginationMixin, PaginateByMixin,
        DateTimeRangeListMixin, SortableListMixin, CommonViewMixin, ListView):
    """View for reporting on users."""
    model = User
    template_name = 'userreport_list.html'
    valid_order_by = [
        'last_name', 'email', 'phone', 'zip', 'state', 'date_joined',
        'last_login', 'flags_received', 'total_groups_joined', 'messages_sent',
        'is_staff', 'is_superuser', 'is_banned', 'phone', 'zip_code', 'state',
        'visit_count', 'unsubscribed'
    ]
    default_order_by = 'date_joined'
    date_range_field = 'date_joined'
    nav_active_item = 'Admin'
    dd_active_item = 'User Report'
    paginate_by = 25
    context_object_name = 'users'

    def get_queryset(self):
        """Update the queryset with some annotations."""
        # Using annotate() on this query will result in a GROUP_BY of all
        # the columns returned. This causes a huge hit on performance, so we
        # need to fall back to the Django ORM's `extra()` functionality.
        queryset = super(UserReportListView, self).get_queryset().extra(
            select={
                'visit_count': "SELECT COUNT(*) FROM accounts_visit visit "
                               "WHERE visit.user_id = accounts_user.id",

                'messages_sent': "SELECT COUNT(*) FROM "
                                 "connectmessages_message messages WHERE "
                                 "messages.sender_id = accounts_user.id",

                'total_groups_joined': "SELECT COUNT(*) FROM "
                                       "notifications_subscription "
                                       "subscriptions WHERE "
                                       "subscriptions.user_id = "
                                       "accounts_user.id",

                'flags_received': "SELECT COUNT(message_flags.id) FROM "
                                  "connectmessages_message messages LEFT JOIN "
                                  "connectmessages_message_flags "
                                  "message_flags ON message_flags.message_id "
                                  "= messages.id WHERE messages.sender_id = "
                                  "accounts_user.id"
            }
        ).defer('biography').defer('image')

        search_name = self.request.GET.get('search_name', False)
        if search_name:
            queryset = queryset.filter(
                Q(first_name__icontains=search_name)
                | Q(last_name__icontains=search_name)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super(UserReportListView, self).get_context_data(**kwargs)
        context['search_name'] = self.request.GET.get('search_name', False)
        return context

    def render_to_response(self, context, **response_kwargs):
        """If exporting, generate a csv."""
        if 'export' in self.request.GET:
            data = Dataset()
            data.headers = (
                u'Name', u'Email', u'Phone', u'Zip', u'State', u'Joined',
                u'Last login', u'Total Groups Joined',
                u'Flags received', u'Messages sent', u'Staff?', u'Superuser?',
                u'Banned?', u'Visits'
            )

            for user in self.get_queryset():
                data.append((
                    user, user.email, user.phone, user.zip_code, user.state,
                    user.date_joined, user.last_login,
                    user.total_groups_joined,
                    user.flags_received, user.messages_sent,
                    user.is_staff, user.is_superuser, user.is_banned,
                    user.visit_count
                ))

            response = HttpResponse(
                data.csv,
                content_type='text/csv'
            )
            response['Content-Disposition'] = 'attachment; filename=users.csv'
            return response
        else:
            return super(UserReportListView, self).render_to_response(
                context, **response_kwargs)


class GroupReportListView(
        PaginationMixin, PaginateByMixin, DateTimeRangeListMixin,
        SortableListMixin, CommonViewMixin, ListView):
    """View for reporting on groups."""
    model = Group
    template_name = 'group_report.html'
    valid_order_by = [
        'group__name', 'message_count', 'thread_count', 'reply_count',
        'posters', 'flagged', 'category', 'state', 'member_count',
        'owner_count', 'created_at', 'created_by', 'image_count',
        'image_clicks', 'link_count', 'link_clicks', 'private', 'published',
        'moderated', 'featured', 'member_list_published'
    ]
    paginate_by = 25
    context_object_name = 'groups'

    def get_queryset(self):
        """Update the queryset with some annotations."""
        return super(GroupReportListView, self).get_queryset().annotate(
            message_count=Count('thread__message', distinct=True),
            thread_count=Count('thread', distinct=True),
            posters=Count('thread__message__sender', distinct=True),
            flagged=Count('thread__message__flags', distinct=True),
            member_count=Count('group__user', distinct=True),
            owner_count=Count('owners', distinct=True),
            image_count=Count('thread__message__images', distinct=True),
            image_clicks=Sum('thread__message__images__view_count'),
            link_count=Count('thread__message__links', distinct=True),
            link_clicks=Sum('thread__message__links__click_count')
        ).extra(
            select={
                'reply_count': """
                    SELECT COUNT(*) from connectmessages_message AS m
                    JOIN connectmessages_thread t
                    ON m.thread_id = t.id
                    WHERE t.group_id = groups_group.id AND
                    m.id != t.first_message_id
                """
            }
        ).prefetch_related('tagged_items__tag')

    def render_to_response(self, context, **response_kwargs):
        """If exporting, generate a csv."""
        if 'export' in self.request.GET:
            data = Dataset()
            data.headers = (
                'Name', 'Messages', 'Threads', 'Replies', 'Posters',
                'Flagged messages', 'Category', 'Tags', 'State', 'Members',
                'Admins', 'Private', 'Published', 'Moderated', 'Featured',
                'Member list published', 'Created', 'Created By', 'Photos',
                'Photo clicks', 'Links', 'Link clicks'
            )

            for group in self.get_queryset():
                data.append((
                    group.group.name, group.message_count, group.thread_count,
                    group.reply_count, group.posters, group.flagged,
                    group.category.name, groups_tags_string([group]),
                    group.state, group.member_count, group.owner_count,
                    group.private, group.published, group.moderated,
                    group.featured, group.member_list_published,
                    group.created_at, group.created_by, group.image_count,
                    group.image_clicks or 0, group.link_count,
                    group.link_clicks or 0
                ))

            response = HttpResponse(
                data.csv,
                content_type='text/csv'
            )
            response['Content-Disposition'] = 'attachment; filename=groups.csv'
            return response
        else:
            return super(GroupReportListView, self).render_to_response(
                context, **response_kwargs)
