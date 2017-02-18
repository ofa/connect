"""Tests for reporting.views."""
# pylint: disable=invalid-name
import csv
import io

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.test.utils import override_settings
from model_mommy import mommy
from tablib import import_set

from open_connect.connectmessages.tests import ConnectMessageTestCase
from open_connect.connect_core.utils.basetests import ConnectTestMixin
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
        self.assertEqual(user.messages_sent, 2)
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
        self.assertEqual(data.width, 14)

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
            reverse('users_report'), {'search': 'Jill'})
        self.assertContains(response, 'Jill')
        self.assertNotContains(response, 'Jack')

    def test_fitler_by_users_last_name(self):
        """Filter by last names."""
        mommy.make(User, last_name='Gaga')
        mommy.make(User, last_name='Spears')
        response = self.client.get(
            reverse('users_report'), {'search': 'Gaga'})
        self.assertContains(response, 'Gaga')
        self.assertNotContains(response, 'Spears')

    def test_filter_by_email(self):
        """Filter by email"""
        mommy.make(User, first_name='Bob', email='bob@bobsemail.com')
        mommy.make(User, first_name='Julie', email='julie@juliesemail.com')
        response = self.client.get(
            reverse('users_report'), {'search': 'bob@bobsemail.com'})
        self.assertContains(response, 'Bob')
        self.assertNotContains(response, 'Julie')

    def test_search_name_in_context(self):
        """Search name should populate in context."""
        response = self.client.get(
            reverse('users_report'), {'search': 'Robyn'})
        self.assertEqual(response.context['search'], 'Robyn')


class GroupReportListViewTest(ConnectTestMixin, TestCase):
    """Tests for GroupReportListView."""
    def setUp(self):
        """Login the testcase as a superuser"""
        self.login(self.create_superuser())

    def test_export(self):
        """
        If export is in query string, response should be a csv.

        We can also take advantage of the easily-parsable result here to test
        the overall report.
        """
        member_one = self.create_user()
        member_two = self.create_user()
        owner = self.create_superuser(
            first_name='Group', last_name='Reporter Exporter')

        group = self.create_group(created_by=owner, featured=True)
        group.owners.add(owner)

        member_one.add_to_group(group.pk)
        member_two.add_to_group(group.pk)

        self.create_thread(sender=member_one, group=group)

        response = self.client.get(
            '{path}?export&search_name={group_name}'.format(
                path=reverse('groups_report'), group_name=group.group.name))
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename=groups.csv'
        )
        self.assertEqual(
            response['Content-Type'],
            'text/csv'
        )

        # We can use python's CSV parsing functionality by creating a CSV file
        # object and passing it to DictReader.
        reader = csv.DictReader(io.StringIO(unicode(response.content)))

        # We can get the first row in the CSV (which should just be our group)
        # by using python's next() functionality.
        report = next(reader)

        self.assertEqual(report['Admins'], '1')
        self.assertEqual(report['Category'], 'Default')
        self.assertEqual(report['Created By'], 'Group R.')
        self.assertEqual(report['Featured'], 'True')
        self.assertEqual(report['Member list published'], 'True')
        self.assertEqual(report['Members'], '2')
        self.assertEqual(report['Messages'], '1')
        self.assertEqual(report['Name'], group.group.name)
        self.assertEqual(report['Posters'], '1')
        self.assertEqual(report['Private'], 'False')
        self.assertEqual(report['Threads'], '1')

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

    def test_search_name_filter(self):
        """Test the 'Search By Name' Filter"""
        self.create_group(group__name='FilterTest1')
        self.create_group(group__name='FilterTest2')

        response = self.client.get(
            reverse('groups_report'), {'search_name': 'FilterTest1'})

        self.assertIn('FilterTest1', response.content)
        self.assertNotIn('FilterTest2', response.content)

    def test_search_name_in_context(self):
        """Search name should populate in context."""
        response = self.client.get(
            reverse('groups_report'), {'search_name': 'Puppies'})
        self.assertEqual(response.context['search_name'], 'Puppies')
