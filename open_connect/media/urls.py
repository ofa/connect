"""URLs for the media application."""
# pylint: disable=invalid-name,no-value-for-parameter

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import permission_required

from open_connect.media import views


# Image urls
urlpatterns = patterns(
    '',
    url(r'^image/create/$', views.upload_photos_view, name='create_image'),
    url(r'^image/promote/$', views.promote_image_view, name='promote_image'),
    url(r'^image/demote/$', views.demote_image_view, name='demote_image'),
    url(r'^image/(?P<image_uuid>[\d\w-]+)/(?P<image_type>\w+)/$',
        views.image_view,
        name='custom_image_version'),
    url(r'^image/(?P<image_uuid>[\d\w-]+)/thumbnail/$',
        views.image_view,
        name='thumbnail',
        kwargs={'image_type': 'thumbnail'}),
    url(r'^image/(?P<image_uuid>[\d\w-]+)/$', views.image_view, name='image'),
    url(r'^my-images/$', views.my_images_view, name='my_images'),
    url(r'^admin-gallery/$',
        permission_required(
            'media.can_access_admin_gallery', raise_exception=True
        )(views.AdminGalleryView.as_view()),
        name='admin_gallery')
)

# ShortenedURL urls
urlpatterns += patterns(
    '',
    url(r'^r/(?P<code>[\d\w]+)/$',
        views.shortened_url_redirect,
        name='shortened_url_redirect'),
    url(r'^urls/$', views.URLPopularityView.as_view(), name='url_popularity')
)
