# -*- coding: utf-8 -*-
"""Tests for connectmessages.models."""
# pylint: disable=invalid-name, protected-access
from textwrap import dedent
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django.utils.timezone import now
from mock import patch
from model_mommy import mommy
import pytz

from open_connect.connectmessages.models import Message, UserThread, Thread
from open_connect.connectmessages.tasks import send_system_message
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import ConnectTestMixin


USER_MODEL = get_user_model()


class ThreadPublicManagerByUserTest(ConnectTestMixin, TestCase):
    """ThreadPublicManager.by_user tests."""
    def test_by_user_user_is_in_group(self):
        """Should return threads that user is a part of."""
        recipient = self.create_user()
        thread = self.create_thread(recipient=recipient)
        result = Thread.public.by_user(user=recipient)
        self.assertIn(thread, result)

    def test_by_user_user_is_not_in_group_or_recipient(self):
        """Should not have threads the user is not a part of."""
        thread = self.create_thread()
        user = self.create_user()
        result = Thread.public.by_user(user=user)
        self.assertNotIn(thread, result)

    def test_invisible_thread(self):
        """Should not have threads that are marked invisible."""
        thread = self.create_thread(visible=False)
        result = Thread.public.by_user(thread.recipients.first())
        self.assertNotIn(thread, result)

    def test_first_message_sender_is_banned(self):
        """Threads started by banned members should not be visible."""
        group = mommy.make('groups.Group')
        normal_user = self.create_user()
        normal_user.add_to_group(group.pk)
        banned_user = self.create_user(is_banned=True)
        thread = self.create_thread(sender=banned_user, group=group)

        # normal_user should not see the thread from the banned user
        result = Thread.public.by_user(normal_user)
        self.assertNotIn(thread, result)

    def test_first_message_sender_is_banned_and_is_user(self):
        """Threads started by banned member are visible to the banned member."""
        group = mommy.make('groups.Group')
        banned_user = self.create_user(is_banned=True)
        banned_user.add_to_group(group.pk)
        thread = self.create_thread(sender=banned_user, group=group)

        result = Thread.public.by_user(banned_user)
        self.assertIn(thread, result)

    def test_non_active_userthread(self):
        """Userthreads that are not active should not be in the by_user"""
        user = self.create_user()
        thread = self.create_thread(recipient=user)

        UserThread.objects.filter(
            thread=thread, user=user).update(status='deleted')

        result = Thread.public.by_user(user)
        self.assertNotIn(thread, result)

    def test_userthread_status(self):
        """The current userthread_status should be selected."""
        thread = self.create_thread()
        thread = Thread.public.by_user(thread.test_shortcuts['recipient'])
        self.assertEqual(thread[0].userthread_status, 'active')


class ThreadPublicManagerByGroupTest(ConnectTestMixin, TestCase):
    """ThreadPublicManager.by_group tests."""
    def test_by_group(self):
        """Should return threads posted to the group."""
        thread = self.create_thread()
        result = Thread.public.by_group(thread.group)
        self.assertIn(thread, result)

    def test_by_group_no_messages_for_another_group(self):
        """Should not have threads posted to another group."""
        thread = self.create_thread()
        other_group = mommy.make('groups.Group')
        result = Thread.public.by_group(thread.group)
        self.assertNotIn(other_group, result)

    def test_invisible_thread(self):
        """Should not have threads that are marked invisible."""
        thread = self.create_thread(visible=False)
        result = Thread.public.by_group(thread.group)
        self.assertNotIn(thread, result)

    def test_first_message_sender_is_banned(self):
        """Threads started by banned members should not be visible."""
        banned_user = self.create_user(is_banned=True)
        thread = self.create_thread(sender=banned_user)
        result = Thread.public.by_group(thread.group)
        self.assertNotIn(thread, result)

    def test_group_is_private(self):
        """Private groups should not have their threads exposed."""
        group = mommy.make('groups.Group', private=True)
        thread = self.create_thread(group=group)
        result = Thread.public.by_group(group)
        self.assertNotIn(thread, result)


@override_settings(TIME_ZONE='US/Central')
class ThreadTest(ConnectTestMixin, TestCase):
    """Thread model tests."""
    def test_unicode(self):
        """Unicode conversion should be Thread and the id of the thread."""
        thread = mommy.prepare('connectmessages.Thread')
        self.assertEqual(str(thread), "Thread %s" % thread.subject)

    def test_add_user_to_thread(self):
        """Test that add_user_to_thread adds the user to the thread."""
        thread = self.create_thread()
        user = self.create_user()
        thread.add_user_to_thread(user)
        self.assertTrue(
            UserThread.objects.filter(thread=thread, user=user).exists())

    def test_get_absolute_url(self):
        """Test get_absolute_url"""
        thread = self.create_thread()
        self.assertEqual(
            thread.get_absolute_url(),
            '/messages/id/{pk}/'.format(
                pk=thread.pk)
        )

    def test_get_unsubscribe_url(self):
        """Test the get_unsubscribe_url method on the Thread model"""
        thread = self.create_thread()
        self.assertEqual(
            thread.get_unsubscribe_url(),
            reverse('thread_unsubscribe', args=[thread.pk])
        )

    def test_group_serializable(self):
        """Test the thread serialization method for a group message"""
        sender = self.create_user()
        thread = self.create_thread(sender=sender)

        message = thread.first_message
        chicago = pytz.timezone('US/Central')
        self.assertDictEqual(
            thread.serializable(),
            {
                'id': thread.pk,
                'total_messages': '1',
                'json_url': reverse('thread_details_json', args=[thread.pk]),
                'subject': thread.subject,
                'snippet': unicode(message.snippet),
                'read': None,
                'group': unicode(thread.group),
                'group_url': reverse(
                    'group_details', kwargs={'pk': thread.group.pk}),
                'group_id': thread.group.pk,
                'type': 'group',
                'unread_messages': 1,
                'category': str(thread.group.category.slug),
                'reply_url': reverse(
                    'create_reply', args=[thread.pk]),
                'unsubscribe_url': thread.get_unsubscribe_url(),
                'is_system_thread': False,
                'userthread_status': None,
                'latest_message_at':
                    str(thread.latest_message.created_at.astimezone(chicago))
            }
        )

    def test_direct_serializable(self):
        """Test the thread serialization method for a direct message"""
        sender = self.create_user()
        recipient = self.create_user()
        thread = self.create_thread(
            direct=True, sender=sender, recipient=recipient)

        message = thread.first_message
        chicago = pytz.timezone('US/Central')
        self.assertDictItemsEqualUnordered(
            thread.serializable(),

            {
                'id': thread.pk,
                'total_messages': '1',
                'subject': thread.subject,
                'snippet': unicode(message.snippet),
                'recipients': [
                    str(sender),
                    str(recipient)
                ],
                'json_url': str(
                    reverse('thread_details_json', args=[thread.pk])),
                'read': None,
                'group': u'',
                'group_url': '',
                'group_id': None,
                'type': 'direct',
                'unread_messages': 1,
                'category': u'',
                'reply_url': reverse(
                    'create_direct_message_reply', args=[thread.pk]),
                'unsubscribe_url': thread.get_unsubscribe_url(),
                'is_system_thread': False,
                'userthread_status': None,
                'latest_message_at':
                    str(thread.latest_message.created_at.astimezone(chicago))
            }
        )

    @override_settings(SYSTEM_USER_EMAIL='systemuser-email@connect.local')
    def test_systemthread(self):
        """Test the thread serialization method for a system message"""
        # The sqlite test runner doesn't run south migrations, so create the
        # user here if it doesn't exist
        USER_MODEL.objects.get_or_create(
            email='systemuser-email@connect.local', defaults={
                'username': 'systemuser-email@connect.local',
                'is_active': True,
                'is_superuser': True
            }
        )
        recipient = self.create_user()
        send_system_message(recipient, 'Subject Here', 'Content Here')
        thread = Thread.public.by_user(recipient).first()

        message = thread.first_message
        chicago = pytz.timezone('US/Central')
        self.assertDictItemsEqualUnordered(
            thread.serializable(),
            {
                'id': thread.pk,
                'total_messages': '1',
                'subject': thread.subject,
                'snippet': unicode(message.snippet),
                'json_url': str(
                    reverse('thread_details_json', args=[thread.pk])),
                'read': False,
                'group': u'',
                'group_url': '',
                'group_id': None,
                'type': 'direct',
                'unread_messages': 1,
                'category': u'',
                'reply_url': reverse(
                    'create_direct_message_reply', args=[thread.pk]),
                'unsubscribe_url': thread.get_unsubscribe_url(),
                'is_system_thread': True,
                'userthread_status': 'active',
                'latest_message_at':
                    str(thread.latest_message.created_at.astimezone(chicago))
            }
        )


class ThreadLastReadAndUnreadCountTest(ConnectTestMixin, TestCase):
    """Tests for last_read_at and unread_messages attributes."""
    def test_last_read_at(self):
        """last_read_at should be correctly set."""
        recipient = self.create_user()
        thread = self.create_thread(recipient=recipient)
        last_read_at = datetime.datetime(
            2014, 3, 17, 19, 42, 37, tzinfo=pytz.timezone('UTC'))
        UserThread.objects.filter(
            thread=thread, user=recipient).update(last_read_at=last_read_at)
        result = Thread.public.by_user(
            user=recipient,
            queryset=Thread.objects.filter(pk=thread.pk)
        ).first()
        self.assertEqual(
            result.last_read_at, last_read_at)
        self.assertEqual(result.serializable()['unread_messages'], 1)

    def test_unread_message_count_thread_never_opened(self):
        """If thread has never been opened, count should equal all messages."""
        recipient = self.create_user()
        thread = self.create_thread(recipient=recipient)
        mommy.make(Message, thread=thread, sender=self.create_superuser())
        result = Thread.public.by_user(
            user=recipient,
            queryset=Thread.objects.filter(pk=thread.pk)
        ).first()
        self.assertEqual(
            result.last_read_at, None)
        self.assertEqual(result.serializable()['unread_messages'], 2)


@override_settings(TIME_ZONE='US/Central')
class MessageTest(ConnectTestMixin, TestCase):
    """Tests for Message model."""
    def test_get_absolute_url_resolves_to_threads(self):
        """get_absolute_url should resolve to threads."""
        thread = self.create_thread()
        self.assertEqual(
            thread.first_message.get_absolute_url(),
            '/messages/id/{pk}/'.format(
                pk=thread.pk)
        )

    def test_serializable(self):
        """Test serializable values."""
        thread = self.create_thread()
        message = thread.first_message
        self.assertEqual(
            message.serializable(),
            {
                'group': unicode(thread.group),
                'reply_url': reverse(
                    'create_reply', args=[thread.pk]),
                'flag_url': reverse(
                    'flag_message', kwargs={'message_id': message.pk}
                ),
                'sent_at': str(
                    message.created_at.astimezone(
                        pytz.timezone('US/Central')
                    )
                ),
                'sender': {
                    'sender': str(message.sender),
                    'sender_is_staff' : message.sender.is_staff,
                    'sender_url': reverse(
                        'user_details',
                        kwargs={'user_uuid': message.sender.uuid}
                    ),
                },
                'text': message.text,
                'read': None,
                'is_system_message': False,
                'pending': False,
                'id': message.pk,
                'snippet': message.snippet
            }
        )

    def test_serizable_pending(self):
        """Test the 'pending' logic in message.serlizable"""
        thread = self.create_thread()
        message = thread.first_message

        # Confirm that an 'approved' message is not marked as pending
        self.assertEqual(message.status, 'approved')
        self.assertEqual(message.serializable()['pending'], False)

        message.status = 'pending'
        message.save()
        self.assertEqual(message.status, 'pending')
        self.assertEqual(message.serializable()['pending'], True)

        # A flagged message should appear the same as an approved thread to the
        # end-user
        message.status = 'flagged'
        message.save()
        self.assertEqual(message.status, 'flagged')
        self.assertEqual(message.serializable()['pending'], False)

    def test_text_cleaner(self):
        """Test _text_cleaner()."""
        text = """
            <html>This is HTML
            Yes it is </html>"""
        message = Message(text=dedent(text))
        result = message._text_cleaner()
        self.assertEqual(result, 'This is HTML Yes it is')

    def test_save_calls_text_cleaner(self):
        """Test that save calls _text_cleaner()."""
        thread = self.create_thread()
        with patch.object(Message, '_text_cleaner') as mock:
            mock.return_value = ''
            self.assertEqual(mock.call_count, 0)
            thread.first_message.save()
            self.assertEqual(mock.call_count, 1)

    def test_long_snippet(self):
        """Long Snippet should return first 140 characters of clean_text."""
        message = Message(clean_text=''.join('x' for _ in range(0, 200)))
        self.assertEqual(
            message.long_snippet,
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxx'
        )

    def test_snippet_short(self):
        """Short messages w/em dash should return all ASCII stripped text"""
        # Em dashes are turned into double dashes, stripped from end
        message = Message(clean_text=u'short — test—   ')
        self.assertEqual(
            message.snippet,
            'short -- test'
        )

    def test_snippet_long_unicode(self):
        """Test a unicode-filled string replaces the unicode character"""
        message = Message(clean_text=u"This sentence — pauses a bit")
        self.assertEqual(
            message.snippet,
            'This sentence -- paus...'
        )

    def test_snippet_long_strip_end(self):
        """Test long unicode-filled snippets ending with a non-letter"""
        # Without stripping the non-character end this would end with ' --'
        message = Message(clean_text=u"This was a longer — sentence")
        self.assertEqual(
            message.snippet,
            'This was a longer...'
        )

    def test_snippet_beginning_nonletter(self):
        """Test a long snippet that starts and ends with a non-letter"""
        message = Message(clean_text=u"!I already know what this will be!!!!!")
        self.assertEqual(
            message.snippet,
            'I already know what...'
        )


class MessageShortenTest(ConnectTestMixin, TestCase):
    """Tests for shortening links in a message."""
    def test_links_in_message_are_shortened(self):
        """Links in a message should be replaced with short code."""
        thread = mommy.make(Thread)
        message = Message(
            text='This is a <a href="http://www.razzmatazz.local">link</a>',
            thread=thread,
            sender=self.create_user()
        )
        message.save()
        self.assertEqual(message.links.count(), 1)
        self.assertTrue(message.links.get().short_code in message.text)

    def test_links_in_message_are_not_shortened(self):
        """If shorten=False, links in message should not be replaced."""
        thread = mommy.make(Thread)
        message = Message(
            text='This is a <a href="http://www.razzmatazz.local">link</a>',
            thread=thread,
            sender=self.create_user()
        )
        message.save(shorten=False)
        self.assertEqual(message.links.count(), 0)
        self.assertTrue('www.razzmatazz.local' in message.text)

    def test_shorten_increments_message_count(self):
        """Increment message_count if the same url is used multiple times."""
        sender = self.create_user()
        thread = self.create_thread(sender=sender)
        thread.first_message.text = (
            'This is a <a href="http://www.razzmatazz.local">link</a>')
        thread.first_message.save()
        message2 = Message.objects.create(
            text='This is a <a href="http://www.razzmatazz.local">link</a>',
            thread=thread,
            sender=sender
        )
        self.assertEqual(message2.links.get().message_count, 2)

    def test_non_http_links_not_shortened(self):
        """Non http/s links shouldn't be shortened."""
        thread = mommy.make(Thread)
        message = Message(
            text='This is an email: <a href="mailto:a@b.local">lnk</a>',
            thread=thread,
            sender=self.create_user()
        )
        message.save()
        self.assertEqual(message.links.count(), 0)


@override_settings(SYSTEM_USER_EMAIL='systemuser-email@connect.local')
class InitialStatusTestTest(ConnectTestMixin, TestCase):
    """Test for determining the initial status of a message"""
    def test_system_message_approved(self):
        """Test that a system message is always approved"""
        system_user, _ = USER_MODEL.objects.get_or_create(
            email='systemuser-email@connect.local', defaults={
                'username': 'systemuser-email@connect.local',
                'is_active': True,
                'is_superuser': True
            }
        )
        thread = self.create_thread(sender=system_user, direct=True)

        self.assertEqual(thread.first_message.get_initial_status(), 'approved')

    def test_user_can_send_up_to_10_dms(self):
        """User should be able to send up to 10 dms before they're pending."""
        user = self.create_user()
        threads = [
            self.create_thread(direct=True, sender=user) for _ in range(0, 10)
        ]

        for thread in threads:
            self.assertEqual(
                thread.first_message.get_initial_status(), 'approved')

        should_be_pending = self.create_thread(direct=True, sender=user)
        self.assertEqual(
            should_be_pending.first_message.get_initial_status(), 'pending'
        )

    def test_superuser_unlimited_direct_messages(self):
        """Superusers should be able to send an unlimited number of DMs"""
        user = self.create_user(is_superuser=True)
        threads = [
            self.create_thread(direct=True, sender=user) for _ in range(0, 11)
        ]

        for thread in threads:
            self.assertEqual(
                thread.first_message.get_initial_status(), 'approved')


class MessageDeleteTest(ConnectTestMixin, TestCase):
    """Tests for deleting a message."""
    def test_no_deleted_messages_in_query(self):
        """Deleted messages shouldn't be in regular queries."""
        thread = self.create_thread()
        thread.first_message.delete()
        self.assertNotIn(thread.first_message, Message.objects.all())

    def test_deleted_messages_in_with_deleted_query(self):
        """Deleted messages should show in with_deleted queries."""
        thread = self.create_thread()
        thread.first_message.delete()
        self.assertTrue(
            Message.objects.with_deleted().filter(
                pk=thread.first_message.pk).exists()
        )

    def test_delete(self):
        """Delete should mark a message as deleted and update the thread."""
        # Create a thread with two messages
        thread = self.create_thread()
        message = mommy.make(
            Message, thread=thread, sender=thread.first_message.sender)

        # Delete the second message
        message = Message.objects.get(pk=message.pk)
        message.delete()

        # Verify the thread now has one message
        thread = Thread.objects.get(pk=thread.pk)
        self.assertEqual(thread.total_messages, 1)

        # Verify the message status is now deleted
        deleted_message = Message.objects.with_deleted().get(pk=message.pk)
        self.assertEqual(deleted_message.status, 'deleted')

    def test_delete_message_is_first_message(self):
        """Delete should update thread.first_message if message was first."""
        # Create a thread with two messages
        thread = self.create_thread()
        message = mommy.make(
            Message, thread=thread, sender=thread.first_message.sender)

        # Delete the first message
        thread = Thread.objects.get(pk=thread.pk)
        thread.first_message.delete()

        # Verify that thread.first_message is updated to what was the second.
        thread = Thread.objects.get(pk=thread.pk)
        self.assertEqual(thread.first_message, message)

    def test_delete_message_is_latest_message(self):
        """Delete should update thread.latest_message if message was last."""
        # Create a thread with two messages
        thread = self.create_thread()
        message = mommy.make(
            Message, thread=thread, sender=thread.first_message.sender)

        # Delete the second message
        message = Message.objects.get(pk=message.pk)
        message.delete()

        # Verify that thread.latest_message is updated to what was the first.
        thread = Thread.objects.get(pk=thread.pk)
        self.assertEqual(thread.latest_message, thread.first_message)

    def test_delete_message_is_only_message_in_thread(self):
        """Delete should mark a thread as deleted if it was the only message."""
        thread = self.create_thread()
        thread.first_message.delete()
        thread = Thread.objects.with_deleted().get(pk=thread.pk)
        self.assertEqual(thread.status, 'deleted')
        self.assertEqual(thread.total_messages, 0)


class MessageFlagTest(ConnectTestMixin, TestCase):
    """Tests for flagging a message."""
    def test_flag(self):
        """Flagging a message 1 time should mark it as pending."""
        recipient = self.create_user()
        thread = self.create_thread(recipient=recipient)
        message = thread.first_message
        self.assertEqual(message.status, 'approved')
        message.flag(recipient)
        self.assertEqual(message.flags.count(), 1)
        self.assertEqual(message.status, 'flagged')


class TestMessagesForUser(ConnectMessageTestCase):
    """Tests for Thread.messages_for_user method."""
    def setUp(self):
        """Setup the TestMessageForUser TestCase"""
        self.user = mommy.make(USER_MODEL)
        group = mommy.make('groups.Group')
        self.user.add_to_group(group.pk)
        self.sender = mommy.make(USER_MODEL, is_superuser=True)
        self.thread = mommy.make(
            'connectmessages.Thread', recipients=[self.user])

    def test_get_message_new(self):
        """New message should not be marked as read."""
        message = mommy.make(
            'connectmessages.Message', thread=self.thread, sender=self.sender)
        thread = Thread.public.by_user(user=self.user)[0]
        messages = thread.messages_for_user(self.user)
        self.assertEqual(messages[0], message)
        self.assertFalse(messages[0].read)

    def test_get_message_read(self):
        """A message that has been read should show up as read."""
        message = mommy.make(
            'connectmessages.Message', thread=self.thread, sender=self.sender)
        user_thread = UserThread.objects.get(
            thread=self.thread, user=self.user)
        user_thread.read = True
        user_thread.save()
        thread = Thread.public.by_user(user=self.user)[0]
        messages = thread.messages_for_user(self.user)
        self.assertEqual(messages[0], message)
        self.assertTrue(messages[0].read)

    def test_get_message_reply(self):
        """New replies should have just the read messages marked read."""
        message1 = mommy.make(
            'connectmessages.Message', thread=self.thread, sender=self.sender)
        message1.created_at = now() - datetime.timedelta(days=1)
        message1.save()
        message2 = mommy.make(
            'connectmessages.Message', thread=self.thread, sender=self.sender)
        message2.created_at = now() - datetime.timedelta(hours=2)
        message2.save()

        # thread.last_read_at is normally set by the by_user query
        self.thread.last_read_at = now() - datetime.timedelta(hours=3)
        messages = self.thread.messages_for_user(self.user)

        # Messages are returned sorted from newest to oldest
        self.assertEqual(messages[0], message2)
        self.assertFalse(messages[0].read)
        self.assertEqual(messages[1], message1)
        self.assertTrue(messages[1].read)


class TestVisibleToUser(ConnectTestMixin, TestCase):
    """Tests for the Message.visible_to_user method."""
    def test_user_is_group_member_status_is_approved(self):
        """User should see approved messages in groups they belong to."""
        group = mommy.make('groups.Group', moderated=True)
        thread = self.create_thread(group=group)
        message = thread.first_message
        message.status = 'approved'
        message.save()
        user = self.create_user()
        user.add_to_group(group.pk)
        self.assertTrue(message.visible_to_user(user))

    def test_user_is_group_member_status_is_not_approved(self):
        """User should not see unapproved messages."""
        group = mommy.make('groups.Group', moderated=True)
        thread = self.create_thread(group=group)
        message = thread.first_message
        message.status = 'pending'
        message.save()
        user = self.create_user()
        user.add_to_group(group.pk)
        self.assertFalse(message.visible_to_user(user))

    def test_group_is_not_private_user_is_not_member(self):
        """User should see approved messages in any non-private group."""
        thread = self.create_thread()
        user = self.create_user()
        self.assertTrue(thread.first_message.visible_to_user(user))

    def test_group_is_private_user_is_not_member(self):
        """Non-members should not see messages in private groups."""
        thread = self.create_thread()
        thread.group.private = True
        thread.save()
        message = thread.first_message
        user = self.create_user()
        self.assertFalse(message.visible_to_user(user))

    def test_user_is_superuser(self):
        """Superusers should see anything, including deleted messages."""
        super_user = self.create_superuser()
        regular_user = self.create_user()
        thread = self.create_thread(status='deleted')
        message = thread.first_message
        self.assertTrue(message.visible_to_user(super_user))
        self.assertFalse(message.visible_to_user(regular_user))

    def test_user_is_sender(self):
        """Senders should always have access to non-deleted messages."""
        sender = self.create_user()
        thread = self.create_thread(sender=sender, status='pending')
        self.assertTrue(thread.first_message.visible_to_user(sender))

    def test_user_is_group_moderator(self):
        """Group moderators should see any message sent to their group."""
        thread = self.create_thread()
        user = self.create_user()
        thread.group.owners.add(user)
        message = thread.first_message
        message.status = 'pending'
        message.save()
        self.assertTrue(message.visible_to_user(user))

    def test_user_is_global_moderator(self):
        """Group moderators should see any message sent to their group."""
        thread = self.create_thread()
        user = self.create_user()
        message = thread.first_message
        message.status = 'pending'
        message.save()

        self.assertFalse(message.visible_to_user(user))

        self.add_perm(user, 'can_moderate_all_messages', 'accounts', 'user')

        # To get rid of the user permission cache we should re-grab our user
        latest_user = USER_MODEL.objects.get(pk=user.pk)
        self.assertTrue(message.visible_to_user(latest_user))

    def test_user_is_recipient(self):
        """Recipients of a thread should see approved messages."""
        recipient = self.create_user()
        thread = self.create_thread(recipient=recipient)
        self.assertTrue(thread.first_message.visible_to_user(recipient))

    def test_recipient_flag_set_true(self):
        """
        If message.is_recipient is true, users should see approved messages.
        """
        recipient = self.create_user()
        group = mommy.make('groups.Group', private=True)
        thread = self.create_thread(group=group)
        self.assertFalse(thread.first_message.visible_to_user(recipient))
        setattr(thread.first_message, 'is_recipient', '1')
        self.assertTrue(thread.first_message.visible_to_user(recipient))

    def test_user_is_sender_message_is_moderated(self):
        """The sender of a message should be able to see their own message."""
        thread = self.create_thread()
        message = thread.first_message
        message.status = 'pending'
        message.save()
        self.assertTrue(message.visible_to_user(message.sender))

    def test_message_is_vetoed(self):
        """Vetoed messages should not be visible to anyone."""
        thread = self.create_thread()
        message = thread.first_message
        message.status = 'vetoed'
        message.save()
        self.assertFalse(message.visible_to_user(message.sender))


class TestThreadGetByUser(TestCase):
    """Tests for Thread.get_by_user."""
    def setUp(self):
        """Setup the TestThreadGetByUser Testcase"""
        # Create a private group
        self.group = mommy.make('groups.Group', private=True)
        self.user = mommy.make(
            'accounts.User', is_active=True, invite_verified=True)
        self.thread = mommy.make(
            'connectmessages.Thread', group=self.group)
        sender = mommy.make('accounts.User')
        sender.add_to_group(self.group.pk)
        mommy.make(
            'connectmessages.Message', thread=self.thread, sender=sender)

    def test_thread_is_not_moderated(self):
        """Return thread if it is posted to a public group."""
        self.assertRaises(
            ObjectDoesNotExist,
            Thread.public.get_by_user,
            **{'thread_id': self.thread.pk, 'user': self.user}
        )
        self.group.private = False
        self.group.save()
        self.assertEqual(
            Thread.public.get_by_user(
                thread_id=self.thread.pk, user=self.user),
            self.thread
        )

    def test_user_is_superuser(self):
        """Return thread if user is a superuser."""
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual(
            Thread.public.get_by_user(
                thread_id=self.thread.pk, user=self.user),
            self.thread
        )

    def test_user_is_recipient(self):
        """Return thread if user is a recipient."""
        UserThread.objects.create(user=self.user, thread=self.thread)
        self.assertEqual(
            Thread.public.get_by_user(
                thread_id=self.thread.pk, user=self.user),
            self.thread
        )

    def test_user_is_group_member(self):
        """Return thread if user is a group member."""
        self.user.add_to_group(self.thread.group.pk)
        self.assertEqual(
            Thread.public.get_by_user(
                thread_id=self.thread.pk, user=self.user),
            self.thread
        )

    def test_user_is_group_owner(self):
        """Return thread if user is a group owner."""
        self.thread.group.owners.add(self.user)
        self.assertEqual(
            Thread.public.get_by_user(
                thread_id=self.thread.pk, user=self.user),
            self.thread
        )

    def test_user_does_not_have_access(self):
        """Raise ObjectDoesNotExist if user doesn't have access."""
        self.assertRaises(
            ObjectDoesNotExist,
            Thread.public.get_by_user,
            **{'thread_id': self.thread.pk, 'user': self.user}
        )


class TestUserThread(ConnectTestMixin, TestCase):
    """Tests for the UserThread model."""
    def test_delete(self):
        """Delete should mark the UT as deleted."""
        thread = self.create_thread()
        ut = UserThread.objects.get(
            user=thread.recipients.first(), thread=thread)
        ut_id = ut.pk
        ut.delete()
        ut = UserThread.objects.with_deleted().get(pk=ut_id)
        self.assertEqual(ut.status, 'deleted')

    def test_archive(self):
        """Should mark UT as archived."""
        thread = self.create_thread()
        ut = UserThread.objects.get(
            user=thread.recipients.first(), thread=thread)
        ut_id = ut.pk
        ut.archive()
        ut = UserThread.objects.get(pk=ut_id)
        self.assertEqual(ut.status, 'archived')
