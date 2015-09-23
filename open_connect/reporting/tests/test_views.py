"""Tests for reporting.views."""
# pylint: disable=invalid-name
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import Client
from django.test.utils import override_settings
from model_mommy import mommy
from tablib import import_set

from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.reporting.views import UserReportListView, GroupReportListView


User = get_user_model()


class UserReportListViewTest(ConnectMessageTestCase):
    """Tests for UserReportListView."""
    def test_get_queryset(self):
        """get_queryset should add the correct extra attributes."""
        # Create a fresh user
        user = User.objects.create_user(
            username='hjkdhds@12ioavoi3.local', password='moo')
        user.add_to_group(self.group1.pk)

        # Create a fresh message and flag it
        thread = mommy.make('connectmessages.Thread', group=self.group1)
        message = mommy.make(
            'connectmessages.Message', sender=user, thread=thread)
        mommy.make('connectmessages.Message', sender=user, thread=thread)
        message.flag(flagged_by=self.staff_user)

        # Authenticate the user so they have a visit count
        middleware = list(settings.MIDDLEWARE_CLASSES)
        if ('open_connect.middleware.visit_tracking.VisitTrackingMiddleware'
                not in middleware):
            middleware.insert(
                0,
                'open_connect.middleware.visit_tracking.'
                'VisitTrackingMiddleware'
                )
        with override_settings(MIDDLEWARE_CLASSES=middleware):
            client = Client()
            client.post(
                reverse('login'),
                {'username': 'hjkdhds@12ioavoi3.local', 'password': 'moo'}
            )

        # Get the queryset
        view = UserReportListView()
        view.request = self.request_factory.get('/')
        queryset = view.get_queryset()

        # Make sure everything looks right
        user = queryset.get(pk=user.pk)
        self.assertEqual(user.flags_received, 1)
        self.assertEqual(user.message_count, 2)
        self.assertEqual(user.visit_count, 1)

    def test_export(self):
        """If export is in query string, response should be a csv."""
        response = self.client.get('%s?export' % reverse('users_report'))
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename=users.csv'
        )
        self.assertEqual(
            response['Content-Type'],
            'text/csv'
        )
        data = import_set(response.content)
        # There should be at least the header row and one user row
        self.assertGreater(data.height, 2)
        self.assertEqual(data.width, 16)

    def test_non_export(self):
        """If export is not in query string, response should be normal."""
        response = self.client.get(reverse('users_report'))
        self.assertEqual(
            response['Content-Type'],
            'text/html; charset=utf-8'
        )
        self.assertEqual(
            response.templates[0].name,
            'userreport_list.html'
        )

    def test_filter_by_users_first_name(self):
        """Filter by first names."""
        mommy.make(User, first_name='Jack')
        mommy.make(User, first_name='Jill')
        response = self.client.get(
            reverse('users_report'), {'search_name': 'Jill'})
        self.assertContains(response, 'Jill')
        self.assertNotContains(response, 'Jack')

    def test_fitler_by_users_last_name(self):
        """Filter by last names."""
        mommy.make(User, last_name='Gaga')
        mommy.make(User, last_name='Spears')
        response = self.client.get(
            reverse('users_report'), {'search_name': 'Gaga'})
        self.assertContains(response, 'Gaga')
        self.assertNotContains(response, 'Spears')

    def test_search_name_in_context(self):
        """Search name should populate in context."""
        response = self.client.get(
            reverse('users_report'), {'search_name': 'Robyn'})
        self.assertEqual(response.context['search_name'], 'Robyn')


class GroupReportListViewTest(ConnectMessageTestCase):
    """Tests for GroupReportListView."""
    def test_get_queryset(self):
        """get_queryset should add the correct extra attributes."""
        # Create a fresh group
        group = mommy.make('groups.Group', make_m2m=True)

        # Create a fresh message and flag it
        thread = mommy.make('connectmessages.Thread', group=group)
        mommy.make(
            'connectmessages.Message', sender=self.superuser, thread=thread)
        mommy.make(
            'connectmessages.Message', sender=self.superuser, thread=thread)
        mommy.make(
            'connectmessages.Message', sender=self.superuser, thread=thread)

        # Get the queryset
        view = GroupReportListView()
        view.request = self.request_factory.get('/')
        queryset = view.get_queryset()

        # Make sure everything looks right
        group = queryset.get(pk=group.pk)
        self.assertEqual(group.reply_count, 2)

    def test_export(self):
        """If export is in query string, response should be a csv."""
        response = self.client.get('%s?export' % reverse('groups_report'))
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename=groups.csv'
        )
        self.assertEqual(
            response['Content-Type'],
            'text/csv'
        )
        data = import_set(response.content)
        # There should be at least the header row and one group row
        self.assertGreaterEqual(data.height, 2)
        self.assertEqual(data.width, 22)

    def test_non_export(self):
        """If export is not in query string, response should be normal."""
        response = self.client.get(reverse('groups_report'))
        self.assertEqual(
            response['Content-Type'],
            'text/html; charset=utf-8'
        )
        self.assertEqual(
            response.templates[0].name,
            'group_report.html'
        )
