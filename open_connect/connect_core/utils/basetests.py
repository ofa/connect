"""Custom TestCase for Connect with some extra goodies in it."""
# pylint: disable=no-self-use
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, modify_settings
from django.utils.timezone import now
from model_mommy import mommy

import open_connect.groups.models as group_models

USER_MODEL = get_user_model()


class ConnectTestMixin(object):
    """Mixin for common testing operations"""
    def create_user(self, **kwargs):
        """Creates a new Connect user."""
        kwargs.setdefault('is_active', True)
        kwargs.setdefault('invite_verified', True)
        kwargs.setdefault('tos_accepted_at', now())
        kwargs.setdefault('ucoc_accepted_at', now())
        user = mommy.make('accounts.User', **kwargs)

        if 'username' not in kwargs:
            user.username = user.email

        user.set_password(kwargs.get('password', 'moo'))
        user.save()
        return user

    def create_superuser(self, **kwargs):
        """Creates a Connect superuser."""
        kwargs['is_superuser'] = True
        kwargs['is_staff'] = True
        user = self.create_user(**kwargs)
        return user

    def add_perm(self, user, codename, app_label, model):
        """Test utility to add a permission to a user"""
        permission = Permission.objects.get_by_natural_key(
            codename, app_label, model)
        user.user_permissions.add(permission)

        # Save the user object to break the permission cache
        user.save(update_fields=['modified_at'])

    def create_group(self, **kwargs):
        """Creates a group."""
        group = mommy.make('groups.Group', **kwargs)
        return group

    def clear_categories(self):
        """
        Delete all categories to allow group slug tests

        As the `slug` field of Category is unique, but we still want to be able
        to test custom category slugs/names, we need to be able to clean our
        `Category` table. We cannot, however, delete the default category.
        """
        group_models.Category.objects.exclude(pk=1).delete()

    def create_thread(self, sender=None, recipient=None, group=None,
                      direct=False, create_message=True,
                      create_recipient=True, **kwargs):
        """Creates a thread."""
        if not sender:
            sender = self.create_user()
        if not recipient and create_recipient:
            recipient = self.create_user()
        if not group and not direct:
            group = self.create_group()
        if group:
            sender.add_to_group(group.pk)
            thread_type = 'group'
        else:
            thread_type = 'direct'

        if recipient:
            thread = mommy.make(
                'connectmessages.Thread',
                thread_type=thread_type,
                recipients=[recipient],
                group=group,
                **kwargs
            )
        else:
            thread = mommy.make(
                'connectmessages.Thread',
                thread_type=thread_type,
                group=group,
                **kwargs
            )
        # By default create the first message
        if create_message:
            mommy.make('connectmessages.Message', sender=sender, thread=thread)
        # Makes it easier to access these objects in the tests.
        thread.test_shortcuts = {
            'sender': sender,
            'recipient': recipient,
            'group': group
        }
        return thread

    # pylint: disable=invalid-name
    def assertQuerysetItemsEqual(self, qs1, qs2):
        """Checks that two querysets have the same items.

        Does not check order of querysets.
        """
        self.assertQuerysetEqual(
            qs1,
            [repr(item) for item in qs2],
            ordered=False
        )

    def assertDictItemsEqualUnordered(self, dict1, dict2):
        """Checks that two dicts are equal.

        If a value is a list of tuple, the items are checked but not the order.
        """
        for key, value in dict1.iteritems():
            if isinstance(value, (list, tuple)):
                self.assertItemsEqual(dict2[key], value)
            else:
                self.assertEqual(dict2[key], value)

    def login(self, user):
        """Shortcut for logging a user in.

        Requires that the child class also has a self.client that is a Django
        test client.
        """
        self.client.login(username=user.username, password='moo')


class ConnectTestCase(TestCase):
    """Custom TestCase for Connect with some extra goodies in it."""
    # pylint: disable=invalid-name
    @classmethod
    def setUpClass(cls):
        """Class setup functionality"""
        super(ConnectTestCase, cls).setUpClass()
        cls.user_model = get_user_model()

        jack = USER_MODEL.objects.filter(username='bo@dj.local')
        if jack.exists():
            cls.user1 = jack.get()
        else:
            cls.user1 = cls.user_model.objects.create_superuser(
                'bo@dj.local', password='moo')
            cls.user1.invite_verified = True
            cls.user1.tos_accepted_at = now()
            cls.user1.ucoc_accepted_at = now()
            cls.user1.save()
        cls.superuser = cls.user1

        grace = USER_MODEL.objects.filter(
            username='gracegrant@razzmatazz.local')
        if grace.exists():
            cls.user2 = grace.get()
        else:
            cls.user2 = cls.user_model.objects.create_user(
                'gracegrant@razzmatazz.local', password='moo')
            cls.user2.invite_verified = True
            cls.user2.tos_accepted_at = now()
            cls.user2.ucoc_accepted_at = now()
            cls.user2.save()
        cls.normal_user = cls.user2

        carson = USER_MODEL.objects.filter(username='carson@razzmatazz.local')
        if carson.exists():
            cls.user3 = carson.get()
        else:
            cls.user3 = cls.user_model.objects.create_user(
                'carson@razzmatazz.local', password='moo')
            cls.user3.invite_verified = True
            cls.user3.tos_accepted_at = now()
            cls.user3.ucoc_accepted_at = now()
            cls.user3.save()

        staff_user = USER_MODEL.objects.filter(
            username='staffuser@razzmatazz.local')
        if staff_user.exists():
            cls.staff_user = staff_user.get()
        else:
            cls.staff_user = cls.user_model.objects.create_user(
                'staffuser@razzmatazz.local', password='moo')
            cls.staff_user.is_staff = True
            cls.staff_user.invite_verified = True
            cls.staff_user.tos_accepted_at = now()
            cls.staff_user.ucoc_accepted_at = now()
            cls.staff_user.save()

    def assertQuerysetItemsEqual(self, qs1, qs2):
        """Checks that two querysets have the same items.

        Does not check order of querysets.
        """
        self.assertQuerysetEqual(
            qs1,
            [repr(item) for item in qs2],
            ordered=False
        )
