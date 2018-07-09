from django.conf.urls import patterns, include, url
from rest_framework.urlpatterns import format_suffix_patterns
from allauth.account.views import confirm_email as allauthemailconfirmation

from connect_api import views

urlpatterns = [
    url(r'^auth/', include('rest_auth.urls')),
    url(r'^auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$',
        allauthemailconfirmation, name="account_confirm_email"),

    url(r'^auth/registration/', include('rest_auth.registration.urls')),

    url(r'users/$', views.UserList.as_view()),
    url(r'users/(?P<pk>[0-9]+)/$', views.UserDetail.as_view()),

    url(r'users/(?P<user_id>[0-9]+)/groups/$', views.groups_a_user_is_member),

    url(r'groups/(?P<group_id>[0-9]+)/members/(?P<user_id>[0-9]+)', views.add_user_to_group),
    url(r'groups/(?P<group_id>[0-9]+)/members/$', views.group_members),

    url(r'groups/(?P<group_id>[0-9]+)/members/owners$', views.group_owners),

    url(r'groups/$', views.GroupList.as_view()),
    url(r'groups/(?P<pk>[0-9]+)/$', views.GroupDetail.as_view()),

]

urlpatterns = format_suffix_patterns(urlpatterns)
