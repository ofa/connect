"""URL definitions for connectmessages app."""
# pylint: disable=no-value-for-parameter,invalid-name

from django.conf.urls import patterns, url
from django.views.generic.base import RedirectView

from open_connect.connectmessages import views


urlpatterns = patterns(
    'open_connect.connectmessages.views',

    # JSON with the number of unread threads
    url(r'^unread-message-count/$',
        views.unread_message_count_view,
        name='unread_message_count'),
    # JSON for a list of threads
    url(r'^json/threads/$',
        views.ThreadJSONListView.as_view(),
        name='thread_json'),

    # JSON for all the messages in a thread
    url(r'^(?P<pk>\d+)/json/$',
        views.ThreadJSONDetailView.as_view(),
        name='thread_details_json'),

    # URLs for composing a message
    url(r'^create/$',
        views.GroupMessageCreateView.as_view(),
        name='create_message'),
    url(r'^(?P<group_id>\d+)/group_message/$',
        views.SingleGroupMessageCreateView.as_view(),
        name='create_group_message'),
    url(r'^(?P<thread_id>\d+)/reply/$',
        views.MessageReplyView.as_view(),
        name='create_reply'),
    url(r'create-direct/(?P<user_uuid>[\d\w-]+)/$',
        views.DirectMessageCreateView.as_view(),
        name='create_direct_message'),
    url(r'^(?P<thread_id>\d+)/direct-reply/$',
        views.DirectMessageReplyView.as_view(),
        name='create_direct_message_reply'),

    # URLs for managing a message
    url(r'^messages/(?P<message_id>\d+)/flag/$',
        views.message_flag_view,
        name='flag_message'),

    # Allows a user to unsubscribe from open_connect.notifications for a
    # single thread.
    url(r'^(?P<thread_id>\d+)/unsubscribe/$',
        'thread_unsubscribe_view',
        name='thread_unsubscribe'),

    # Message Moderation (uses backbone)
    url(r'^mod/(?P<thread_id>\d+)/msg/(?P<message_id>\d+)/$',
        views.InboxView.as_view(), name='message_mod'),

    # The root inbox (uses backbone)
    url(r'^$', views.InboxView.as_view(), name='threads'),

    # Individual Sections (inbox/archive/unread) (uses backbone)
    url(r'^(?P<section>inbox|archive|unread)/$',
        views.InboxView.as_view(), name='threads_section'),

    # Individual groups in individual sections (uses backbone)
    url(r'^(?P<section>inbox|archive|unread)/group/(?P<group_id>\d+)/$',
        views.InboxView.as_view(), name='threads_section_group'),

    # Individual groups inbox (uses backbone)
    url(r'^inbox/group/(?P<group_id>\d+)/$',
        views.InboxView.as_view(), name='threads_group'),

    # Individual thread (uses backbone)
    url(r'^id/(?P<thread_id>\d+)/$',
        views.InboxView.as_view(), name='thread'),

    # Non-existent directories in backbone paths should redirect
    url(r'^(id|(inbox|archive|unread)/group|mod)/$',
        RedirectView.as_view(url='/messages/'), name='thread'),

)
