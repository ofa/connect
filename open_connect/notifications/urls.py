"""URL definitions for notifications app."""
# pylint: disable=invalid-name,no-value-for-parameter

from django.conf.urls import patterns, url

from open_connect.notifications import views


urlpatterns = patterns(
    'notifications.views',
    url(r'^update/$',
        views.SubscriptionsUpdateView.as_view(),
        name='update_subscriptions'),
    url(r'^update/(?P<group_id>\d+)/$',
        views.SubscriptionUpdateView.as_view(),
        name='update_subscription'),
    url(r'^unsubscribe/(?P<user_id>\d+)/(?P<key>[A-Za-z0-9_\-]+)/$',
        views.LoggedOutSubscriptionView.as_view(),
        name='logged_out_update_subscription')
)
