"""Tests for notifications.views."""
# pylint: disable=no-value-for-parameter, invalid-name

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.test import Client, TestCase, RequestFactory
from django.http import Http404
from model_mommy import mommy

from open_connect.groups.models import Group
from open_connect.notifications import views
from open_connect.notifications.models import Subscription
from open_connect.connectmessages.tests import ConnectMessageTestCase


class SubscriptionsUpdateViewTest(ConnectMessageTestCase):
    """Tests for SubscriptionsUpdateView."""
    def setUp(self):
        """Setup the SubscriptionUpdateViewTest TestCase"""
        self.subscription1 = Subscription.objects.create(
            user=self.user2, group=self.group)
        self.group2 = Group.objects.create(name='Group Two')
        self.subscription2 = Subscription.objects.create(
            user=self.user2, group=self.group2
        )

    def test_group_name_added_to_forms(self):
        """Test that group_name is added to each form instance."""
        subscription_update_view = views.SubscriptionsUpdateView.as_view()
        request = self.request_factory.get('/')
        request.user = self.user2
        response = subscription_update_view(request)
        for form in response.context_data['formset']:
            self.assertEqual(form.group_name, form.instance.group.group.name)

    def test_redirects_to_update_subscriptions_on_success(self):
        """Test that successful post redirects to update subscriptions."""
        client = Client()
        client.post(
            reverse('login'),
            {'username': 'gracegrant@razzmatazz.local', 'password': 'moo'}
        )
        self.assertEqual(self.subscription1.period, 'immediate')
        response = client.post(
            reverse('update_subscriptions'),
            {
                'form-0-id': self.subscription1.pk,
                'form-0-kind': 'web',
                'form-0-period': 'daily',
                'form-TOTAL_FORMS': 1,
                'form-INITIAL_FORMS': 1,
                'form-MAX_NUM_FORMS': 1000
                }
        )
        subscription1 = Subscription.objects.get(pk=self.subscription1.pk)
        self.assertEqual(subscription1.period, 'daily')
        self.assertRedirects(response, reverse('update_subscriptions'))

    def test_redirects_to_next_on_success(self):
        """If next is provided in the querystring, redirect user to that url."""
        client = Client()
        client.post(
            reverse('login'),
            {'username': 'gracegrant@razzmatazz.local', 'password': 'moo'}
        )
        self.assertEqual(self.subscription1.period, 'immediate')
        next_page = reverse(
            'user_details', kwargs={'user_uuid': self.user2.uuid})
        response = client.post(
            '%s?next=%s' % (reverse('update_subscriptions'), next_page),
            {
                'form-0-id': self.subscription1.pk,
                'form-0-kind': 'web',
                'form-0-period': 'daily',
                'form-TOTAL_FORMS': 1,
                'form-INITIAL_FORMS': 1,
                'form-MAX_NUM_FORMS': 1000
                }
        )
        subscription1 = Subscription.objects.get(pk=self.subscription1.pk)
        self.assertEqual(subscription1.period, 'daily')
        self.assertRedirects(response, next_page)

    def test_only_contains_subscriptions_for_logged_in_user(self):
        """Test that subscriptions for other users aren't in context."""
        other_user_subscription = Subscription.objects.create(
            user=self.user1, group=self.group
        )
        subscription_update_view = views.SubscriptionsUpdateView.as_view()
        request = self.request_factory.get('/')
        request.user = self.user2
        response = subscription_update_view(request)
        subscription_list = response.context_data['subscription_list']
        self.assertNotIn(other_user_subscription, subscription_list)
        self.assertIn(self.subscription1, subscription_list)
        self.assertIn(self.subscription2, subscription_list)


class SubscriptionUpdateViewTest(TestCase):
    """Tests for SubscriptionUpdateView."""
    def setUp(self):
        """Setup the SubscriptionUpdateViewTest TestCase"""
        self.view = views.SubscriptionUpdateView()
        factory = RequestFactory()
        self.view.request = factory.get('/')
        self.user = mommy.make('accounts.User')
        self.group = mommy.make('groups.Group')
        self.user.add_to_group(self.group.pk)
        self.view.request.user = self.user
        self.view.kwargs = {'group_id': self.group.pk}

    def tearDown(self):
        """Teardown/Close Out the SubscriptionUpdateViewTest TestCase"""
        self.user.subscriptions.all().delete()
        self.user.delete()
        self.group.delete()

    def test_success_url_return_url_in_post(self):
        """View should redirect to return_url if it is in POST values."""
        self.view.request.POST = {'return_url': '/somewhere/'}
        result = self.view.get_success_url()
        self.assertEqual(result, '/somewhere/')

    def test_success_url(self):
        """View should default to django get_success_url without return_url."""
        self.assertRaises(ImproperlyConfigured, self.view.get_success_url)

    def test_get_object(self):
        """get_object should return the subscription."""
        result = self.view.get_object()
        subscription = Subscription.objects.get(
            user=self.user, group=self.group)
        self.assertEqual(result, subscription)


class LoggedOutSubscriptionsUpdateViewTest(TestCase):
    """
    Test for view where user is not logged in but must still be able to
    unsubscribe
    """
    def test_queryset(self):
        """
        Test the queryset returned when various kwargs are passed to the view
        """
        user = mommy.make('accounts.User')
        group = mommy.make(Group)
        subscription = mommy.make(
            Subscription, user=user, group=group)
        view = views.LoggedOutSubscriptionView()
        view.kwargs = {
            'user_id': user.pk,
            'key': 'fakekey'
        }
        with self.assertRaises(Http404):
            view.get_queryset()
        view.kwargs['key'] = user.private_hash
        subscriptions = view.get_queryset()
        self.assertIn(subscription, subscriptions)
