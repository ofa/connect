"""URL definitions for accounts app."""
# pylint: disable=no-value-for-parameter,invalid-name

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import permission_required

from open_connect.accounts import views
from open_connect.connectmessages.views import DirectMessageCreateView


urlpatterns = patterns(
    'accounts.views',
    url(r'^update/$',
        views.UserUpdateView.as_view(),
        name='update_user'),
    url(r'^(?P<user_uuid>[\d\w-]+)/permissions/$',
        permission_required('accounts.can_modify_permissions')(
            views.UpdateUserPermissionView.as_view(),
        ),
        name='update_user_permissions'),
    url(r'^(?P<pk>\d+)/message/$',
        DirectMessageCreateView.as_view(),
        name='message_user'),
    url(r'^(?P<user_uuid>[\d\w-]+)/ban/$',
        permission_required('accounts.can_ban')(
            views.BanUserView.as_view(),
        ),
        name='ban_user'),
    url(r'^(?P<user_uuid>[\d\w-]+)/unban/$',
        permission_required('accounts.can_unban')(
            views.UnBanUserView.as_view(),
        ),
        name='unban_user'),
    url(r'^profile/$',
        views.UserProfileRedirectView.as_view(),
        name='user_profile'),
    url(r'^invites/create/$',
        permission_required('accounts.add_invite')(
            views.InviteCreateView.as_view()
        ),
        name='create_invite'),
    url(r'^invites/$',
        permission_required('accounts.add_invite')(
            views.InviteListView.as_view()
        ),
        name='invites'),
    url(r'^enter-invite/$',
        views.InviteEntryView.as_view(),
        name='enter_invite'),
    url(r'^accept-terms/$',
        views.TermsAndConductAcceptView.as_view(),
        name='accept_terms_and_conduct'),
    url(r'^(?P<user_uuid>[\d\w-]+)/become/$',
        permission_required('accounts.can_impersonate')(
            views.BecomeUserView.as_view()
        ),
        name='become_user'),
    url(r'^unbecome-user/$', views.unbecome_user, name='unbecome_user'),
    url(r'^tutorial/$', views.user_tutorial_view, name='user_tutorial'),
    url(r'^(?P<user_uuid>[\d\w-]+)/$',
        views.UserDetailView.as_view(),
        name='user_details')
)
