"""Custom TestCase and helpers for connectmessages tests."""
# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.utils.timezone import now
from model_mommy import mommy

from open_connect.connect_core.utils.basetests import ConnectTestCase
from open_connect.groups.models import Group
from open_connect.connectmessages.models import Message, Thread, UserThread


USER_MODEL = get_user_model()

MESSAGE_TEXT = (
    'This has been a test. This has been a test.'
    ' This has been a test. This has been a test.'
    ' This has been a test. This has been a test.'
    ' This has been a test. This has been a test.'
)
THREAD_SUBJECT = 'Test message'


class ConnectMessageTestCase(ConnectTestCase):
    """Helper TestCase for connectmessages app."""
    # pylint: disable=invalid-name
    @classmethod
    def setUpClass(cls):
        """Setup the TestCase class"""
        super(ConnectMessageTestCase, cls).setUpClass()
        cls.group1 = mommy.make(
            Group, tos_accepted_at=now())
        cls.group2 = mommy.make(Group)

        cls.superuser.add_to_group(cls.group1.pk)
        cls.superuser.add_to_group(cls.group2.pk)
        cls.normal_user.add_to_group(cls.group1.pk)
        cls.staff_user.add_to_group(cls.group1.pk)

        cls.thread1 = mommy.make(
            Thread, group=cls.group1, subject=THREAD_SUBJECT)
        cls.message1 = mommy.make(
            Message, thread=cls.thread1, sender=cls.superuser,
            text=MESSAGE_TEXT, status='approved')
        cls.message2 = mommy.make(
            Message, thread=cls.thread1, sender=cls.normal_user,
            text=MESSAGE_TEXT, status='approved')

        cls.thread2 = mommy.make(
            Thread, group=cls.group2, subject=THREAD_SUBJECT)
        cls.message3 = mommy.make(
            Message, thread=cls.thread2, sender=cls.superuser,
            text=MESSAGE_TEXT, status='approved')

        cls.directthread1 = mommy.make(
            Thread, thread_type='direct', subject=THREAD_SUBJECT)
        cls.directmessage1 = mommy.make(
            Message,
            thread=cls.directthread1,
            sender=cls.user1,
            text=MESSAGE_TEXT,
            status='approved'
        )

        mommy.make(UserThread, user=cls.normal_user, thread=cls.directthread1)
        mommy.make(UserThread, user=cls.staff_user, thread=cls.directthread1)

        cls.request_factory = RequestFactory()
        cls.request = cls.request_factory.get('/')
        setattr(cls.request, 'session', 'session')
        messages = FallbackStorage(cls.request)
        setattr(cls.request, '_messages', messages)
        cls.request.user = cls.superuser
        cls._group = None

    # pylint: disable=invalid-name
    def setUp(self):
        """Setup the test"""
        self.client.post(
            reverse('account_login'),
            {'login': 'bo@dj.local', 'password': 'moo'})

    def message(self, **kwargs):
        """Create a new non-persistent Message."""
        return mommy.prepare(
            Message,
            thread=kwargs.get('thread', self.thread1),
            sender=kwargs.get('user', self.superuser),
            text=kwargs.get('message', MESSAGE_TEXT),
            status=kwargs.get('status', 'approved')
        )

    @property
    def group(self):
        """Cache and return the test group."""
        if not self._group:
            self._group = mommy.make(
                Group, group__name='Test group', published=True)
        return self._group

    # pylint: disable=invalid-name
    def assertSuccess(self, response):
        """Helper method for asserting a response object was successful."""
        self.assertEqual(response.status_code, 200)
