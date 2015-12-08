"""Tests for connectmessages.views."""
# pylint: disable=invalid-name,no-value-for-parameter,protected-access,too-many-lines
from datetime import timedelta, datetime
import json
import random
import time

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotAllowed, HttpResponse, Http404
from django.test import Client, RequestFactory
from django.test import TestCase as DjangoTestCase
from django.test.utils import override_settings
from django.utils.html import escapejs
from django.utils.timezone import now
from mock import patch
from model_mommy import mommy
import pytz

from open_connect.connectmessages import views
from open_connect.connectmessages.forms import GroupMessageForm
from open_connect.connectmessages.models import (
    Message, Thread, UserThread, MESSAGE_STATUSES
)
from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import ConnectTestMixin

USER_MODEL = get_user_model()
ONE_HUNDRED_ONE_RANDOM_CSV_VALUES = (
    '545,362,42,988,904,206,518,676,673,667,843,263,379,609,797,645,878,541,'
    '650,311,902,894,463,318,255,61,218,967,232,109,48,450,322,938,940,552,'
    '175,831,76,739,195,50,715,414,40,305,597,171,843,199,178,623,869,130,119,'
    '865,591,320,761,996,849,549,468,904,352,892,563,672,141,464,613,268,222,'
    '330,654,451,287,229,51,50,916,349,633,922,186,610,231,295,873,149,187,'
    '227,384,155,377,968,269,945,335,345,756'
)


def patch_message_middleware(request):
    """Helper to get django messages middleware to work for testing."""
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    return request


class MessageCreateViewTest(ConnectMessageTestCase):
    """Tests for MessageCreateView."""
    def test_redirects_to_threads(self):
        """test_redirects_to_threads.

        Creating a message redirects to threads."""
        response = self.client.post(
            reverse('create_message'),
            {'subject': 'fjdsklfs', 'text': 'jdfklsj', 'group': self.group1.pk},
            HTTP_USER_AGENT='Chromefox'
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('threads'))

    @override_settings(LOGIN_URL=reverse('login'))
    def test_form_valid_anonymous_user_redirects_to_login(self):
        """Unauthenticated user should be redirected to login."""
        client = Client()
        response = client.post(
            reverse('create_message'),
            {'subject': 'fjdsklfs', 'text': 'jdf', 'group': self.group1.pk}
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '%s?next=%s' % (reverse('login'),
                                      reverse('create_message'))
        )

    def test_get_form_sender_id_is_authenticated_user(self):
        """Sender id should be set to the currently authenticated user."""
        view = views.MessageCreateView()
        view.request = self.request
        view.object = Message()
        form = view.get_form(views.MessageCreateView.form_class)
        self.assertEqual(
            form.instance.sender_id,
            self.request.user.pk
        )

    def test_form_valid(self):
        """Sender, user_agent, and ip_address should be set on form_valid."""
        self.client.post(
            reverse('create_message'),
            {'subject': 'fjdsklfs', 'text': 'jdfklsj', 'group': self.group1.pk},
            HTTP_USER_AGENT='Chromefox',
            HTTP_X_FORWARDED_FOR='7.0.9.3',
            REMOTE_ADDR='1.2.3.4'
        )
        message = Message.objects.latest('pk')
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.user_agent, 'Chromefox')
        self.assertEqual(message.ip_address, '7.0.9.3')

    def test_form_valid_x_forwarded_for_missing(self):
        """Sender, user_agent, and ip_address should be set on form_valid."""
        self.client.post(
            reverse('create_message'),
            {
                'subject': 'fjdsklfs',
                'text': 'jdfklsj',
                'group': self.group1.pk
            },
            HTTP_USER_AGENT='Chromefox',
            REMOTE_ADDR='1.2.3.4'
        )
        message = Message.objects.latest('pk')
        self.assertEqual(message.ip_address, '1.2.3.4')

    def test_form_valid_multiple_ips(self):
        """Test form_valid when there are multiple ip addresses."""
        self.client.post(
            reverse('create_message'),
            {
                'subject': 'fjdsklfs',
                'text': 'jdfklsj',
                'group': self.group1.pk
            },
            HTTP_USER_AGENT='Chromefox',
            REMOTE_ADDR='1.2.3.4, 0.9.8.7'
        )
        message = Message.objects.latest('pk')
        self.assertEqual(message.ip_address, '1.2.3.4')

    def test_get_template_name(self):
        """Template name should default to message_form.html"""
        response = self.client.get(
            reverse('create_message'),
        )
        self.assertEqual(
            response.template_name, 'connectmessages/message_form.html')

    def test_get_template_name_embedded(self):
        """Template name sould be message_form_embedded.html if embed in GET"""
        response = self.client.get(
            '%s?embed=yes' % reverse('create_message'),
        )
        self.assertEqual(
            response.template_name,
            'connectmessages/message_form_embedded.html'
        )


class GroupMessageCreateViewTest(ConnectMessageTestCase):
    """Test GroupMessageCreateView"""
    def test_groups_form_contains_groups_member_of(self):
        """
        Ensure that users can only view groups they're authorized to message
        """
        request_factory = RequestFactory()
        request = request_factory.get('/')

        user = mommy.make(USER_MODEL)
        request.user = user

        view = views.GroupMessageCreateView()
        view.request = request
        view.object = None
        form = view.get_form(GroupMessageForm)

        user.add_to_group(self.group1.pk)
        self.assertIn(self.group1, user.messagable_groups)
        self.assertIn(str(self.group1), form.as_p())
        self.assertNotIn(str(self.group2), form.as_p())

        user.add_to_group(self.group2.pk)
        self.assertIn(self.group2, user.messagable_groups)
        self.assertIn(str(self.group1), form.as_p())
        self.assertIn(str(self.group2), form.as_p())

        user.remove_from_group(self.group1)
        self.assertNotIn(self.group1, user.messagable_groups)
        self.assertNotIn(str(self.group1), form.as_p())


class MessageReplyViewTest(ConnectTestMixin, ConnectMessageTestCase):
    """Tests for MessageReplyView"""
    def setUp(self):
        """Setup the test"""
        super(MessageReplyViewTest, self).setUp()
        request = self.request_factory.get('/')
        self.request = patch_message_middleware(request)
        self.request.user = self.user1
        self.view = views.MessageReplyView.as_view()

    def test_thread_returned_in_context(self):
        """Test that the thread was returned in the context"""
        response = self.view(self.request, thread_id=self.thread1.pk)
        self.assertEqual(response.context_data['thread'], self.thread1)

    def test_messages_returned_in_context(self):
        """Test that the messages were returned in the context"""
        response = self.view(self.request, thread_id=self.thread1.pk)
        self.assertIn(
            self.thread1.first_message,
            response.context_data['connectmessages']
        )

    def test_hide_controls_returned_in_context(self):
        """Test that hide_message_controls was returned in the context"""
        response = self.view(self.request, thread_id=self.thread1.pk)
        self.assertTrue(response.context_data['hide_message_controls'])

    def test_closed_thread_throws_warning(self):
        """Test that a closed thread redirects and throws a warning"""
        thread = mommy.make(Thread, group=self.group1)
        mommy.make(Message, sender=self.user1, thread=thread)

        # Assert that a request with our thread's ID returns correctly
        response = self.view(self.request, thread_id=thread.pk)
        response = self.client.get(reverse('create_reply', args=(thread.pk,)))
        self.assertEqual(response.context_data['thread'], thread)

        # Delete the thread
        thread.closed = True
        thread.save()

        response2 = self.client.get(reverse('create_reply', args=(thread.pk,)))
        self.assertEqual(response2.status_code, 302)
        self.assertIn(
            str(thread),
            response2.cookies['messages'].value
        )

    def test_no_permission_to_post_to_group_throws_warning(self):
        """If a user doesn't have permission to post, redirect them."""
        group = mommy.make('groups.Group')
        thread = mommy.make(Thread, group=group)
        self.user2.add_to_group(group.pk)
        mommy.make(Message, sender=self.user2, thread=thread)

        self.create_user(email='test@reply.local', password='test')
        client = Client()
        client.post(
            reverse('login'),
            {'username': 'test@reply.local', 'password': 'test'}
        )
        response = client.get(reverse('create_reply', args=[thread.pk]))
        self.assertRedirects(response, reverse('threads'))
        self.assertIn('You don\'t have permission to post to this group.',
                      str(response.cookies))

    def test_non_existent_thread_throws_404(self):
        """Test that a thread that does not exist throws a 404 error"""
        thread = mommy.make(Thread, group=self.group1)
        mommy.make(Message, sender=self.user1, thread=thread)

        # Assert that a request with our thread's ID returns correctly
        response = self.view(self.request, thread_id=thread.pk)
        self.assertEqual(response.context_data['thread'], thread)

        # Delete the thread
        thread.delete()

        # Assert that requesting a non-existent thread returns a HTTP404
        with self.assertRaises(Http404):
            self.view(self.request, thread_id=thread.pk)

    def test_form_valid(self):
        """Test the form_valid method on MessageReplyView"""
        random_number = random.randrange(0, 150000)
        text = 'Test %s' % random_number

        request = self.request_factory.post('/', {'text': text})
        request = patch_message_middleware(request)
        request.user = self.user1
        response = self.view(request, thread_id=self.thread1.pk)
        self.assertEqual(response.status_code, 302)

        message = Message.objects.filter(thread=self.thread1).latest('pk')
        self.assertEqual(message.text, text)
        self.assertEqual(message.sender, self.user1)


class TestSingleGroupMessageCreateView(ConnectTestMixin, DjangoTestCase):
    """Message to set group view test"""

    def test_dispatch_unauthorized_user(self):
        """Test the dispatch method for a user who is not allowed to post"""
        user1 = self.create_user()
        self.client.login(username=user1.email, password='moo')
        group = mommy.make('groups.Group')
        response = self.client.post(
            reverse('create_group_message', kwargs={'group_id': group.pk}),
            {'subject': 'anything', 'text': '1275731253', 'group': group.pk}
        )
        self.assertRedirects(response, reverse('threads'))
        self.assertFalse(Message.objects.filter(sender=user1).exists())
        self.assertFalse(Message.objects.filter(thread__group=group).exists())
        self.assertIn('You don\'t have permission to post to this group.',
                      str(response.cookies))

    def test_dispatch_authorized_user(self):
        """Test the dispatch method for a user who is allowed to post"""
        user1 = self.create_user()
        self.client.login(username=user1.email, password='moo')
        group = mommy.make('groups.Group')
        user1.add_to_group(group.pk)
        response = self.client.post(
            reverse('create_group_message', kwargs={'group_id': group.pk}),
            {'subject': 'anything', 'text': '1275731253', 'group': group.pk}
        )
        self.assertRedirects(response, reverse('threads'))
        message = Message.objects.latest('pk')
        self.assertEqual(message.thread.group, group)
        self.assertNotIn('You don\'t have permission to post to this group.',
                         str(response.cookies))

    def test_form_valid(self):
        """Test that a valid form creates a new group messages"""
        user1 = self.create_superuser()
        user2 = self.create_user()
        self.client.login(username=user1.email, password='moo')
        group = mommy.make('groups.Group')
        user1.add_to_group(group.pk)
        user2.add_to_group(group.pk)
        response = self.client.post(
            reverse('create_group_message', kwargs={'group_id': group.pk}),
            {'subject': 'anything', 'text': '1275731253', 'group': group.pk}
        )
        self.assertRedirects(response, reverse('threads'))
        message = Message.objects.latest('pk')
        # Confirm the latest message was sent to our brand new group
        self.assertEqual(message.thread.group, group)

        # Confirm user2 has the new message
        self.assertTrue(
            message.thread.userthread_set.filter(user=user2).exists())


class DirectMessageCreateViewTest(ConnectTestMixin, DjangoTestCase):
    """Direct Message View Test"""
    def setUp(self):
        """Setup the test"""
        self.view = views.DirectMessageCreateView.as_view()
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')
        self.user1 = self.create_superuser(email='a@b.local')
        self.request.user = self.user1

    def test_recipient_returned_in_context(self):
        """Test that the recipient is returned in the context"""
        recipient = self.create_user()

        response = self.view(self.request, user_uuid=recipient.uuid)
        self.assertEqual(response.context_data['recipient'], recipient)

    def test_non_existent_recipient_throws_404(self):
        """
        Test that trying to send a message to a user that does not exist
        returns a 404 error
        """
        user = self.create_user()
        self.view.kwargs = {'user_uuid': '!'}
        response = self.view(self.request, user_uuid=user.uuid)
        self.assertEqual(response.context_data['recipient'], user)

        user.delete()

        with self.assertRaises(Http404):
            self.view(self.request, user_uuid=user.uuid)

    def test_regulaer_user_cannot_direct_message_regular_user(self):
        """Test that 2 'regular' users cannot message one another"""
        sender = self.create_user()
        recipient = self.create_user()
        self.login(sender)

        # Attempt to POST a new direct message to a regular user, sent from
        # another regular user
        response = self.client.post(
            reverse('create_direct_message',
                    kwargs={'user_uuid': recipient.uuid}),
            {'text': 'hello', 'subject': 'quick dm'}
        )

        # Confirm that the user was instead redirected
        self.assertEqual(response.status_code, 302)

        # Confirm that the user received an error
        self.assertIn(
            'You don\'t have permission to direct message {user}'.format(
                user=recipient),
            str(response.cookies)
        )

        # Confirm that no new message was created for the recipient
        self.assertFalse(UserThread.objects.filter(user=recipient).exists())

    def test_regular_user_cannot_get_form_regular_users(self):
        """
        Test that regular users cannot view the form to message regular users
        """
        sender = self.create_user()
        recipient = self.create_user()
        self.login(sender)

        # Attempt to get the create_direct_message form for a regular user as
        # a regular user
        response = self.client.get(
            reverse('create_direct_message',
                    kwargs={'user_uuid': recipient.uuid})
            )

        # Confirm that the user was immediately redirected
        self.assertEqual(response.status_code, 302)

        # Confirm that a permission exception was thrown
        self.assertIn(
            'You don\'t have permission to direct message {user}'.format(
                user=recipient),
            str(response.cookies)
        )

    def test_user_cannot_message_self(self):
        """
        Test that users cannot message themselves.
        """
        sender = self.create_superuser()
        self.login(sender)

        # Attempt to get the sender's create_direct_message form as sender
        response = self.client.get(
            reverse('create_direct_message',
                    kwargs={'user_uuid': sender.uuid})
            )

        # Confirm that the user was immediately redirected
        self.assertEqual(response.status_code, 302)

        # Confirm that a permission exception was thrown
        self.assertIn(
            'You don\'t have permission to direct message {user}'.format(
                user=sender),
            str(response.cookies)
        )

    def test_regular_user_can_get_staff_direct_message_form(self):
        """
        Test that regular users can get the direct message form for staff
        """
        sender = self.create_user()
        staff_member = self.create_user(is_staff=True)
        self.login(sender)

        # Attempt to get the create_direct_message form for a staff member as
        # a regular user
        response = self.client.get(
            reverse('create_direct_message',
                    kwargs={'user_uuid': staff_member.uuid})
            )

        # Confirm that a valid page was returned
        self.assertEqual(response.status_code, 200)

        # Confirm that no permission error was returned
        self.assertNotIn(
            'You don\'t have permission to direct message {user}'.format(
                user=staff_member),
            str(response.cookies)
        )

    def test_regular_user_can_direct_message_staff(self):
        """Test that regular users can direct message staff"""
        sender = self.create_user()
        staff_member = self.create_user(is_staff=True)
        self.login(sender)

        # POST a fake message directed at a staff member
        response = self.client.post(
            reverse('create_direct_message',
                    kwargs={'user_uuid': staff_member.uuid}),
            {'text': 'hello', 'subject': 'quick dm'}
        )

        # Confirm the user is redirected to the "threads" page
        self.assertRedirects(response, reverse('threads'))

        # Confirm that there is not a permission denied message
        self.assertNotIn(
            'You don\'t have permission to direct message {user}'.format(
                user=staff_member),
            str(response.cookies)
        )

        # Confirm that the staff member now has a message
        self.assertEqual(
            UserThread.objects.filter(
                user=staff_member,
                thread__first_message__sender=sender).count(),
            1
        )

    def test_staff_can_direct_message_users(self):
        """Test that staff can direct message regular users"""
        recipient = self.create_user()
        staff_member = self.create_user(is_staff=True)
        self.login(staff_member)

        # As a staff member, attempt to POST a new direct message to a regular
        # user
        response = self.client.post(
            reverse('create_direct_message',
                    kwargs={'user_uuid': recipient.uuid}),
            {'text': 'hello', 'subject': 'quick dm'}
        )

        # Confirm that the staff member was successfully redirected to the list
        # of threads
        self.assertRedirects(response, reverse('threads'))

        # Confirm that no permission-denied error was thrown
        self.assertNotIn(
            'You don\'t have permission to direct message {user}'.format(
                user=recipient),
            str(response.cookies)
        )

        # Confirm that a new message was created in the database sent by the
        # staff member to the regular user
        self.assertEqual(
            UserThread.objects.filter(
                user=recipient,
                thread__first_message__sender=staff_member).count(),
            1
        )

    def test_form_valid(self):
        """Test that a valid form actually creates a new direct message"""
        random_number = random.randrange(0, 150000)
        text = 'Test %s' % random_number
        user2 = self.create_user()

        request = self.request_factory.post(
            '/', {'text': text, 'subject': 'cool'})
        request = patch_message_middleware(request)
        request.user = self.user1
        self.view.kwargs = {'user_uuid': user2.uuid}
        response = self.view(request, user_uuid=user2.uuid)
        self.assertEqual(response.status_code, 302)

        message = Message.objects.filter(
            thread__recipients=user2).latest('pk')
        self.assertEqual(message.text, text)
        self.assertEqual(message.sender, self.user1)

    def test_sender_thread_is_read(self):
        """UserThread should be read for the person who sent a message."""
        recipient = self.create_user()
        self.client.post(
            reverse('login'),
            {'username': self.user1.email, 'password': 'moo'}
        )
        response = self.client.post(
            reverse('create_direct_message',
                    kwargs={'user_uuid': recipient.uuid}),
            {'text': 'hello', 'subject': 'quick dm'}
        )
        self.assertRedirects(response, reverse('threads'))
        sender_userthread = UserThread.objects.filter(
            user=self.user1).latest('pk')
        self.assertTrue(sender_userthread.read)
        self.assertIsNotNone(sender_userthread.last_read_at)

    def test_recipient_thread_is_unread(self):
        """UserThread should be unread for the person receiving a message."""
        recipient = self.create_user()
        self.client.post(
            reverse('login'),
            {'username': self.user1.email, 'password': 'moo'}
        )
        response = self.client.post(
            reverse('create_direct_message',
                    kwargs={'user_uuid': recipient.uuid}),
            {'text': 'hello', 'subject': 'quick dm'}
        )
        self.assertRedirects(response, reverse('threads'))
        recipient_userthread = UserThread.objects.filter(
            user=recipient).latest('pk')
        self.assertFalse(recipient_userthread.read)
        self.assertIsNone(recipient_userthread.last_read_at)


class DirectMessageReplyViewTest(ConnectTestMixin, DjangoTestCase):
    """Test DirectMessageReplyView"""
    @patch.object(views, 'create_recipient_notifications')
    def test_form_valid(self, mock_create_notification):
        """A valid submission should trigger a call to create notifications."""
        # Make sure the sender is staff so their direct message goes through
        sender = self.create_user(is_staff=True)
        self.client.login(username=sender.email, password='moo')

        recipient = self.create_user()

        # Create original DM
        response = self.client.post(
            reverse('create_direct_message',
                    kwargs={'user_uuid': recipient.uuid}),
            {'subject': 'hello', 'text': 'hello'}
        )
        self.assertRedirects(response, reverse('threads'))

        # Reset mock and create reply
        mock_create_notification.reset_mock()
        thread = Thread.objects.get(
            thread_type='direct', recipients=recipient)
        response = self.client.post(
            reverse('create_direct_message_reply',
                    kwargs={'thread_id': thread.pk}),
            {'text': 'hiwgioankldskajl'}
        )
        self.assertRedirects(response, reverse('threads'))

        # Make sure create_recipient_notifications was called once
        message = Message.objects.get(text='hiwgioankldskajl')
        mock_create_notification.delay.assert_called_once_with(message.pk)


class TestThreadJSONDetailView(ConnectTestMixin, DjangoTestCase):
    """Tests for ThreadJSONDetailView."""
    def test_no_matching_thread_raises_404(self):
        """Should raise 404 if there isn't a matching thread."""
        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        response = self.client.get(
            reverse('thread_details_json', kwargs={'pk': 837483}))
        self.assertEqual(response.status_code, 404)

    def test_has_read_and_last_read_at(self):
        """If there's a UserThread, read should be set."""
        user = self.create_user()
        self.client.login(username=user.email, password='moo')
        thread = self.create_thread(sender=user)
        user_thread = UserThread.objects.get(user=user, thread=thread)
        user_thread.read = True
        user_thread.last_read_at = datetime(2014, 04, 28, 12, 0, 0)
        user_thread.save()
        response = self.client.get(
            reverse('thread_details_json', kwargs={'pk': thread.pk}))
        json_response = json.loads(response.content)
        self.assertTrue(json_response['thread']['read'])
        self.assertTrue(json_response['connectmessages'][0]['read'])


class BaseThreadListViewTest(ConnectTestMixin, DjangoTestCase):
    """
    Tests for BaseThreadListView

    We test most of get_queryset() in `ThreadJSONListViewTest` so that we can
    test using Django's test client against an actual view.
    """

    def setUp(self):
        """Set up tests."""
        self.request_factory = RequestFactory()

    def test_get_serialized_threads(self):
        """Test get_serialized_threads()"""
        thread1 = self.create_thread()
        user = thread1.test_shortcuts['sender']
        thread2 = self.create_thread(user)
        threads = Thread.public.by_user(user).filter(
            pk__in=[thread1.pk, thread2.pk])

        view = views.BaseThreadListView()
        view.request = self.request_factory.get('/')
        view.request.user = user

        result = view.get_serialized_threads(threads)

        self.assertEqual(len(result), 2)
        timezone = pytz.timezone('America/Chicago')
        self.assertDictEqual(
            threads[0].serializable(timezone.zone),
            result[0]
        )
        self.assertDictEqual(
            threads[1].serializable(timezone.zone),
            result[1]
        )

    def test_get_js_context_data(self):
        """Test get_js_context_data()"""
        request = self.request_factory.get('/')
        request.user = self.create_user()

        view = views.BaseThreadListView()
        view.request = request

        result = view.get_js_context_data()

        self.assertTrue(result['current_time'] <= int(time.time()))
        self.assertTrue(result['current_time'] > int(time.time() - 300))
        self.assertEqual(result['alerts'], request.user.get_moderation_tasks())

    def test_includes_all_by_default(self):
        """Requesting includes all threads."""
        # Create some threads
        thread1 = self.create_thread()
        user = thread1.test_shortcuts['sender']
        thread2 = self.create_thread(user)

        # Archive one of the threads
        UserThread.objects.filter(
            user=user, thread=thread2).update(status='archived')
        # Pull threads for the user
        threads = Thread.public.by_user(user).filter(
            pk__in=[thread1.pk, thread2.pk]).order_by('pk')

        # Get the mixin
        view = views.BaseThreadListView()
        view.request = self.request_factory.get('/')
        view.request.user = user

        # Should only have thread1
        result = view.get_serialized_threads(threads)
        self.assertEqual(len(result), 2)
        self.assertEqual(thread1.pk, result[0]['id'])
        self.assertEqual(thread2.pk, result[1]['id'])

    def test_archived_threads_included(self):
        """Should include archived threads by default."""
        # Create some threads
        thread1 = self.create_thread()
        user = thread1.test_shortcuts['sender']
        thread2 = self.create_thread(user)

        # Archive one of the threads
        UserThread.objects.filter(
            user=user, thread=thread2).update(status='archived')
        # Pull threads for the user, sorting by pk so we know the order for
        # assertions below.
        threads = Thread.public.by_user(user).filter(
            pk__in=[thread1.pk, thread2.pk]).order_by('pk')

        # Get the mixin
        view = views.BaseThreadListView()
        view.request = self.request_factory.get('/')
        view.request.user = user

        # Should have both threads
        result = view.get_serialized_threads(threads)
        self.assertEqual(len(result), 2)
        self.assertEqual(thread1.pk, result[0]['id'])
        self.assertEqual(thread2.pk, result[1]['id'])


class InboxViewTest(ConnectTestMixin, DjangoTestCase):
    """Tests for InboxView"""
    def setUp(self):
        """Setup for tests."""
        self.user = self.create_user()
        self.login(self.user)

    def test_correct_count_js_context(self):
        """Test that the correct thread count is returned in the JS context"""
        # Create 21 threads
        for _ in range(0, 21):
            self.create_thread(recipient=self.user)

        # Grab all the resulting threads from the database
        threads = Thread.public.by_user(self.user)

        # Confirm we actually created 21 threads
        self.assertEqual(threads.count(), 21)

        response = self.client.get(
            reverse('threads')
        )

        decoded = json.loads(response.context_data['js_context'])

        # Confirm that the correct count of threads (21) was returned
        self.assertEqual(decoded['total_threads'], 21)

    def test_json_on_page(self):
        """Test that the JSON object is actually on the resulting page"""
        self.create_thread()
        response = self.client.get(reverse('threads'))
        escaped_json = escapejs(response.context['js_context'])
        self.assertContains(
            response,
            'JSON.parse("{escaped_json}")'.format(escaped_json=escaped_json)
        )


class ThreadJSONListViewTest(ConnectTestMixin, DjangoTestCase):
    """Tests for ThreadJSONListView."""
    def setUp(self):
        """Setup the ThreadJSONListViewTest"""
        self.user = self.create_user()
        self.client.login(username=self.user.email, password='moo')

    def fetch_userthread(self, thread):
        """Grab the userthread"""
        return thread.userthread_set.get(user=self.user)

    def test_post_no_threads(self):
        """Test that a 404 is thrown when no threads are available to modify"""
        # Attempt to get messages from a group that does not exist
        result = self.client.post(
            reverse('thread_json') + '?group=100000000',
            {'read': 'true'}
        )
        self.assertEqual(result.status_code, 404)

    def test_post_no_changes(self):
        """Test that a POST with no instructions returns a 400"""
        self.create_thread(recipient=self.user)
        self.create_thread(recipient=self.user)

        result = self.client.post(
            reverse('thread_json'),
            {}
        )

        self.assertEqual(result.status_code, 400)
        self.assertDictEqual(
            json.loads(result.content), {'success': False, 'rows': 0})

    def test_post_returns_correct_count(self):
        """Test that the correct number of changes is returned"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        thread3 = self.create_thread(recipient=self.user)

        # Generate a POST url that will only retrun our threads
        url1 = "{path}?id={thread1_pk},{thread2_pk}".format(
            path=reverse('thread_json'),
            thread1_pk=thread1.pk,
            thread2_pk=thread2.pk
        )
        url2 = "{path}?id={thread1_pk},{thread2_pk},{thread3_pk}".format(
            path=reverse('thread_json'),
            thread1_pk=thread1.pk,
            thread2_pk=thread2.pk,
            thread3_pk=thread3.pk
        )

        # Run an update that touches 2 threads
        result1 = self.client.post(
            url1,
            {'read': 'true'}
        )

        self.assertEqual(result1.status_code, 200)
        self.assertDictEqual(
            json.loads(result1.content), {'success': True, 'rows': 2})

        # Run an update that touches 3 threads
        result2 = self.client.post(
            url2,
            {'read': 'true'}
        )

        self.assertEqual(result2.status_code, 200)
        self.assertDictEqual(
            json.loads(result2.content), {'success': True, 'rows': 3})

    def test_post_mark_all_read(self):
        """Test marking all posts as read"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(read=True)

        self.client.post(
            reverse('thread_json'),
            {'read': 'true'}
        )

        self.assertTrue(self.fetch_userthread(thread1).read)
        self.assertTrue(self.fetch_userthread(thread2).read)

    def test_post_mark_unread(self):
        """Test marking posts as unread"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(
                read=True, last_read_at=now())

        self.client.post(
            reverse('thread_json'),
            {'read': 'false'}
        )

        self.assertFalse(self.fetch_userthread(thread1).read)
        self.assertFalse(self.fetch_userthread(thread1).last_read_at)
        self.assertFalse(self.fetch_userthread(thread2).read)
        self.assertFalse(self.fetch_userthread(thread2).last_read_at)

    def test_post_archive(self):
        """Test archiving a thread"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(status='archived')

        self.client.post(
            reverse('thread_json'),
            {'status': 'archived'}
        )

        self.assertEqual(self.fetch_userthread(thread1).status, 'archived')
        self.assertEqual(self.fetch_userthread(thread2).status, 'archived')

    def test_post_active(self):
        """Test activating an archived thread"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(status='archived')

        self.client.post(
            reverse('thread_json'),
            {'status': 'active'}
        )

        self.assertEqual(self.fetch_userthread(thread1).status, 'active')
        self.assertEqual(self.fetch_userthread(thread2).status, 'active')

    def test_post_unsubscribe(self):
        """Test unsubscribing to receiving notifications about threads"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread1).update(subscribed_email=True)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(subscribed_email=False)

        self.client.post(
            reverse('thread_json'),
            {'subscribed': 'false'}
        )

        self.assertFalse(self.fetch_userthread(thread1).subscribed_email)
        self.assertFalse(self.fetch_userthread(thread2).subscribed_email)

    def test_post_subscribe(self):
        """Test subscribing to receiving notifications about threads"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread1).update(subscribed_email=True)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(subscribed_email=False)

        self.client.post(
            reverse('thread_json'),
            {'subscribed': 'true'}
        )

        self.assertTrue(self.fetch_userthread(thread1).subscribed_email)
        self.assertTrue(self.fetch_userthread(thread2).subscribed_email)

    def test_with_since(self):
        """Response should only have newer messages."""
        old_thread = self.create_thread(recipient=self.user)
        new_thread = self.create_thread(recipient=self.user)
        Thread.objects.filter(
            pk=new_thread.pk).update(modified_at=now() + timedelta(hours=10))
        response = self.client.get(
            reverse('thread_json'),
            {'since': str(int(time.time() + 100))}
        )
        self.assertNotContains(response, old_thread.first_message.snippet)
        self.assertContains(response, new_thread.first_message.snippet)

    def test_with_since_is_not_digit(self):
        """Ignore since argument if it's a non-digit."""
        old_thread = self.create_thread(recipient=self.user)
        new_thread = self.create_thread(recipient=self.user)
        response = self.client.get(
            reverse('thread_json'),
            {'since': 'hi'}
        )
        self.assertContains(response, old_thread.first_message.snippet)
        self.assertContains(response, new_thread.first_message.snippet)

    def test_with_id(self):
        """If id is specified, response should only include that thread."""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        response = self.client.get(
            reverse('thread_json'),
            {'id': thread1.pk}
        )
        self.assertContains(response, thread1.first_message.snippet)
        self.assertNotContains(response, thread2.first_message.snippet)

    def test_with_multiple_id(self):
        """Return multiple threads if multiple IDs are presented"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        response = self.client.get(
            reverse('thread_json'),
            {'id': "{id1},{id2}".format(id1=thread1.pk, id2=thread2.pk)}
        )
        self.assertContains(response, thread1.first_message.snippet)
        self.assertContains(response, thread2.first_message.snippet)

    def test_context(self):
        """Context should contain the correct keys.

        The values are tested elsewhere, just checking that they are getting
        added to the context here.
        """
        response = self.client.get(reverse('thread_json'))
        content = json.loads(response.content)
        self.assertIn('current_time', content)
        self.assertIn('alerts', content)
        self.assertIn('paginator', content)

        paginator_content = content['paginator']
        self.assertIn('page_number', paginator_content)
        self.assertIn('total_pages', paginator_content)
        self.assertIn('total_threads', paginator_content)
        self.assertIn('has_other_pages', paginator_content)

    def test_only_active(self):
        """Should exclude archived threads when requesting active threads."""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(status='archived')

        response = self.client.get(
            reverse('thread_json'),
            {'status': 'active'}
        )

        self.assertContains(response, thread1.first_message.snippet)
        self.assertNotContains(response, thread2.first_message.snippet)

    def test_only_archive(self):
        """Should return only archived threads when status arg is 'archived'"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(status='archived')

        response = self.client.get(
            reverse('thread_json'),
            {'status': 'archived'}
        )

        self.assertNotContains(response, thread1.first_message.snippet)
        self.assertContains(response, thread2.first_message.snippet)

    def test_only_specific_group(self):
        """Should return only threads in a specific group"""
        group1 = self.create_group()
        group2 = self.create_group()
        thread1 = self.create_thread(recipient=self.user, group=group1)
        thread2 = self.create_thread(recipient=self.user, group=group2)

        response = self.client.get(
            reverse('thread_json'),
            {'group': group1.pk}
        )

        self.assertContains(response, thread1.first_message.snippet)
        self.assertNotContains(response, thread2.first_message.snippet)

    def test_multiple_groups(self):
        """Should return threads from multiple groups"""
        group1 = self.create_group()
        group2 = self.create_group()
        group3 = self.create_group()
        thread1 = self.create_thread(recipient=self.user, group=group1)
        thread2 = self.create_thread(recipient=self.user, group=group2)
        thread3 = self.create_thread(recipient=self.user, group=group3)

        group_string = "{pk1},{pk2}".format(pk1=group1.pk, pk2=group2.pk)
        response = self.client.get(
            reverse('thread_json'),
            {'group': group_string}
        )

        self.assertContains(response, thread1.first_message.snippet)
        self.assertContains(response, thread2.first_message.snippet)
        self.assertNotContains(response, thread3.first_message.snippet)

    def test_only_read(self):
        """Should return only read threads when the thread is marked read"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(read=True)

        response = self.client.get(
            reverse('thread_json'),
            # By using an uppercase 'True' we're also testing the str-to-bool
            # functionality
            {'read': 'True'}
        )

        self.assertNotContains(response, thread1.first_message.snippet)
        self.assertContains(response, thread2.first_message.snippet)

    def test_only_unread(self):
        """Should return only unread threads when filtered as such"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(read=True)

        response = self.client.get(
            reverse('thread_json'),
            {'read': 'false'}
        )

        self.assertContains(response, thread1.first_message.snippet)
        self.assertNotContains(response, thread2.first_message.snippet)

    def test_ignore_read(self):
        """Should return all threads if no `read` attr is passed"""
        thread1 = self.create_thread(recipient=self.user)
        thread2 = self.create_thread(recipient=self.user)
        UserThread.objects.filter(
            user=self.user, thread=thread2).update(read=True)

        response = self.client.get(
            reverse('thread_json'),
            {}
        )

        self.assertContains(response, thread1.first_message.snippet)
        self.assertContains(response, thread2.first_message.snippet)


class ThreadUnsubscribeViewTest(ConnectMessageTestCase):
    """Tests for thread_unsubscribe_view"""
    def test_thread_unsubscribe(self):
        """View should unsubscribe a user from a thread"""
        request = self.request_factory.post('/')
        request = patch_message_middleware(request)
        request.user = self.user1
        group = mommy.make('groups.Group')
        self.user1.add_to_group(group.pk)

        thread = mommy.make(Thread, group=group)
        mommy.make(Message, thread=thread, sender=self.user1)

        self.assertTrue(UserThread.objects.filter(
            user=self.user1, thread=thread, subscribed_email=True).exists())

        views.thread_unsubscribe_view(request, thread.pk)

        self.assertFalse(UserThread.objects.filter(
            user=self.user1, thread=thread, subscribed_email=True).exists())

    def test_thread_unsubscribe_view_only_accepts_post(self):
        """view should return HttpResponseNotAllowed if request isn't POST."""
        def check_http_method(method, klass):
            """Check HTTP functions"""
            request = getattr(self.request_factory, method)('/')
            request = patch_message_middleware(request)
            request.user = self.staff_user
            result = views.thread_unsubscribe_view(request, self.thread1.pk)
            self.assertIsInstance(result, klass)

        for method in ('put', 'get', 'head', 'delete', 'options'):
            check_http_method(method, HttpResponseNotAllowed)

        check_http_method('post', HttpResponse)


class MessageFlagViewTest(ConnectMessageTestCase):
    """Tests for message_flag_view."""
    def test_message_flag_view(self):
        """view should flag a message and return the expected response."""
        request = self.request_factory.post('/')
        request.user = self.superuser
        message = self.message()
        message.status = 'approved'
        message.save()
        flag_count = message.flags.count()
        result = views.message_flag_view(request, message.pk)
        message = Message.objects.get(pk=message.pk)
        self.assertEqual(message.flags.count(), flag_count + 1)
        json_result = json.loads(result.content)
        self.assertTrue(json_result['success'])
        self.assertEqual(json_result['message_id'], message.pk)

    def test_message_flag_view_only_accepts_post(self):
        """view should return HttpResponseNotAllowed if request isn't POST."""
        def check_http_method(method, klass):
            """Check HTTP functions"""
            request = getattr(self.request_factory, method)('/')
            request.user = self.staff_user
            result = views.message_flag_view(request, self.message1.pk)
            self.assertIsInstance(result, klass)

        for method in ('put', 'get', 'head', 'delete', 'options'):
            check_http_method(method, HttpResponseNotAllowed)

        check_http_method('post', HttpResponse)


class UnreadMessageCountViewTest(ConnectTestMixin, DjangoTestCase):
    """Tests for the unread_message_count view."""
    def setUp(self):
        """Setup the UnreadMessageCountViewTest TestCase"""
        self.user = self.create_user()
        self.group = self.create_group()
        self.user.add_to_group(self.group.pk)
        self.login(self.user)
        self.thread = self.create_thread(group=self.group)
        self.url = reverse('unread_message_count')

    def test_zero_unread_count(self):
        """unread_count should be 0 if there are no unread messages."""
        UserThread.objects.filter(
            user=self.user
        ).update(read=True, last_read_at=now() + timedelta(days=1))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content['unread_count'], 0)
        self.assertEqual(content['success'], True)
        self.assertEqual(content['errors'], [])

    def test_zero_messages_count(self):
        """unread_count should be 0 if user inbox has no messages at all."""
        UserThread.objects.filter(
            thread=self.thread, user=self.user
        ).delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content['unread_count'], 0)
        self.assertEqual(content['success'], True)
        self.assertEqual(content['errors'], [])

    def test_count(self):
        """unread_count should be equal to the number of unread messages."""
        UserThread.objects.filter(
            thread=self.thread, user=self.user
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content['unread_count'], 1)
        self.assertEqual(content['success'], True)
        self.assertEqual(content['errors'], [])

    def test_only_counts_unread_messages(self):
        """Count only unread messages in threads."""
        mommy.make(
            'connectmessages.Message',
            thread=self.thread,
            sender=self.thread.first_message.sender
        )
        self.thread.first_message.created_at = now() - timedelta(days=1)
        self.thread.first_message.save()
        UserThread.objects.filter(
            thread=self.thread, user=self.user
        ).update(last_read_at=now() - timedelta(days=1))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content['unread_count'], 1)
        self.assertEqual(content['success'], True)
        self.assertEqual(content['errors'], [])

    @patch('open_connect.accounts.models.cache')
    def test_count_includes_moderation_tasks(self, mock_cache):
        """Count should include any moderation tasks."""
        mock_cache.get_many.return_value = {
            '{}_messages_to_mod'.format(self.user.pk): 1,
            '{}_groups_to_mod'.format(self.user.pk): 1
        }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content['unread_count'], 3)

    def test_count_includes_only_approved_messages(self):
        """Only approved messages should be included in count."""
        # Create some new messages, one with each valid status
        sender = self.thread.first_message.sender
        thread = self.thread
        for status in MESSAGE_STATUSES:
            message = mommy.make(
                'connectmessages.Message', sender=sender, thread=thread)
            message.status = status[0]
            message.save()

        # Make sure we see them all
        self.assertEqual(
            Message.objects.with_deleted().filter(thread=thread).count(),
            len(MESSAGE_STATUSES) + 1
        )

        # Validate the returned count
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content['unread_count'], 2)
