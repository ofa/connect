"""URL definitions for reporting app."""
# pylint: disable=invalid-name,no-value-for-parameter
from django.conf.urls import patterns, url
from django.contrib.auth.decorators import permission_required

from open_connect.reporting import views


urlpatterns = patterns(
    '',
    url(r'^users/$',
        permission_required('accounts.can_view_user_report')(
            views.UserReportListView.as_view()),
        name='users_report'),
    url(r'^groups/$',
        permission_required('accounts.can_view_group_report')(
            views.GroupReportListView.as_view()),
        name='groups_report'),
)
