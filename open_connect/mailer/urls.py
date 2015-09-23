"""URLs for the mailer app"""
# pylint: disable=no-value-for-parameter,invalid-name, line-too-long
from django.conf.urls import patterns, url

from open_connect.mailer import views

urlpatterns = patterns(
    'open_connect.mailer.views',
    url(r'^unsubscribe/$', views.UnsubscribeView.as_view(), name='unsubscribe'),
    url(r'^unsubscribe/thanks/$', views.UnsubscribeThanksView.as_view(),
        name='unsubscribe_thanks'),
    url(r'^track/o/(?P<encoded_data>[\d\w]+)/(?P<request_hash>[\d\w]+)/track\.gif$',
        views.OpenView.as_view(),
        name='email_open'),
)
