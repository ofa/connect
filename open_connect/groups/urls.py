"""Group urls."""
# pylint: disable=invalid-name,no-value-for-parameter
from django.contrib.auth.decorators import permission_required
from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from open_connect.groups import views


urlpatterns = patterns(
    'groups.views',
    url(r'^create/$',
        permission_required('groups.add_group', raise_exception=True)(
            views.GroupCreateView.as_view()
        ),
        name="create_group"),
    url(r'^(?P<pk>\d+)/update/$',
        views.GroupUpdateView.as_view(),
        name='update_group'),
    url(r'^(?P<pk>\d+)/delete/$',
        permission_required('groups.delete_group', raise_exception=True)(
            views.GroupDeleteView.as_view()
        ),
        name='delete_group'),
    url(r'^(?P<group_id>\d+)/images/$',
        views.GroupImagesView.as_view(),
        name='group_images'),
    url(r'^(?P<pk>\d+)/$',
        views.GroupDetailView.as_view(),
        name='group_details'),
    url(r'^(?P<pk>\d+)/members/$',
        views.GroupMemberListView.as_view(),
        name='group_members'),
    url(r'^(?P<pk>\d+)/invite/$', permission_required('accounts.add_invite')(
        views.GroupMemberInviteView.as_view()),
        name='group_invite'),
    url(r'^(?P<group_id>\d+)/quickadd/$',
        permission_required('accounts.add_invite')(views.group_quick_user_add),
        name='group_quick_user_add'),
    url(r'^$', views.GroupListView.as_view(), name='groups'),
    url(r'^my-groups/$', views.MyGroupsView.as_view(), name='my_groups'),
    url(r'^subscribe/$', views.group_subscribe_view, name='group_subscribe'),
    url(r'^unsubscribe/$',
        views.group_unsubscribe_view,
        name='group_unsubscribe'),
    url(r'^moderate-requests/$',
        views.GroupRequestUpdateView.as_view(),
        name='moderate_requests'),
    url(r'^(?P<group_id>\d+)/remove-user-from-group/(?P<user_uuid>[\d\w-]+)/$',
        views.remove_user_from_group_view,
        name='remove_user_from_group'),

)
