"""URL definitions for resources app."""
# pylint: disable=invalid-name,no-value-for-parameter
from django.conf.urls import patterns, url

from open_connect.resources import views


urlpatterns = patterns(
    '',
    url(r'^create/$',
        views.ResourceCreateView.as_view(), name='create_resource'),
    url(r'^(?P<uuid>[\d\w-]+)/update/$',
        views.ResourceUpdateView.as_view(),
        name='update_resource'),
    url(r'^(?P<uuid>[\d\w-]+)/delete/$',
        views.ResourceDeleteView.as_view(),
        name='delete_resource'),
    url(r'^(?P<slug>[-a-zA-Z0-9_]+)/$',
        views.ResourceDownloadView.as_view(),
        name='resource'),
    url(r'^$', views.ResourceListView.as_view(), name='resources')
)
