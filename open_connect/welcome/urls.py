"""URL definitions for welcome app."""
# pylint: disable=invalid-name,no-value-for-parameter

from django.conf.urls import patterns, url

from open_connect.welcome import views


urlpatterns = patterns(
    'welcome.views',
    url(r'^$', views.WelcomeView.as_view(), name='welcome'),
)
