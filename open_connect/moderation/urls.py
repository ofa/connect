"""urls for the moderation app"""
# pylint: disable=no-value-for-parameter,invalid-name
from django.conf.urls import patterns, url

from open_connect.moderation import views


urlpatterns = patterns(
    'connectmessages.views',
    url(r'^(?P<group>\d+)/$',
        views.ModeratorView.as_view(),
        name='mod_bygroup'),
    url(r'^$', views.ModeratorView.as_view(), name='mod_admin'),
    url(r'^submit/$', views.SubmitView.as_view(), name='mod_submit'),
    url(r'^frequency/$', views.ModerationFrequencyUpdateView.as_view(),
        name='mod_notification_frequency'),
    url(r'^log/$', views.FlagLogView.as_view(), name='flag_log')
)
