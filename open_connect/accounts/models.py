"""Models for user accounts."""
# pylint:disable=too-many-instance-attributes
from datetime import timedelta
import logging

import re
from uuid import uuid4

from django_extensions.db.fields import UUIDField
from django.conf import settings
from django.contrib.auth import models as auth_models
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse_lazy, reverse
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from pytz import common_timezones
import autocomplete_light

from open_connect.accounts.tasks import render_and_send_invite_email
from open_connect.accounts.utils import generate_nologin_hash
from open_connect.groups import tasks as group_tasks
from open_connect.groups.models import Group, GroupRequest
from open_connect.mailer.utils import unsubscribe_url
from open_connect.media.models import Image
from open_connect.notifications.models import NOTIFICATION_PERIODS
from open_connect.connectmessages.models import Message
from open_connect.connect_core.utils.location import STATES
from open_connect.connect_core.utils.models import (
    TimestampModel, CacheMixinModel
)


LOGGER = logging.getLogger('accounts.models')


VALID_TWITTER_RE = re.compile(r'^[\w\d_]{0,15}$')


# Must be a factor of 24 (or 0)
MODERATION_NOTIFICATION_PERIODS = (
    (1, 'Hourly'),
    (4, 'Every 4 Hours'),
    (12, 'Every 12 Hours'),
    (24, 'Once Per Day'),
    (0, 'No New Moderation Notifications')
)


class PermissionDeniedError(BaseException):
    """Raised when permission to post to a group is denied."""
    pass


class UserManager(auth_models.BaseUserManager):
    """Manager for the User model."""
    def create_user(self, username, password=None, **extra_fields):
        """Creates a User with the given username, email and password."""
        from open_connect.mailer.models import Unsubscribe

        email = extra_fields.get('email', username)

        try:
            invite = Invite.objects.get(
                email=email.lower(), consumed_at__isnull=True)
        except ObjectDoesNotExist:
            invite = None

        email = UserManager.normalize_email(email)

        first_name = extra_fields.get('first_name', '')
        last_name = extra_fields.get('last_name', '')

        user = self.model(username=username, email=email,
                          is_staff=False, is_active=True, is_superuser=False,
                          last_login=now(), date_joined=now(),
                          first_name=first_name, last_name=last_name)

        user.set_password(password)
        user.save(using=self._db)

        if invite:
            user = invite.use_invite(user.pk)

        # Remove any unsubscribe records that may exist for this user
        Unsubscribe.objects.filter(address=email).delete()

        return user

    def create_superuser(self, username, password, **extra_fields):
        """Creates a superuser."""
        user = self.create_user(username, password, **extra_fields)
        user.is_staff = True
        user.is_active = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


def validate_twitter_handle(value):
    """Raises a ValidationError if value isn't a valid twitter handle."""
    if not VALID_TWITTER_RE.match(value):
        raise ValidationError(
            u'This is not a valid twitter handle.'
            u' Please enter just the portion after the @.'
        )


class User(
        CacheMixinModel, auth_models.AbstractBaseUser,
        auth_models.PermissionsMixin):
    """User model."""
    TIMEZONE_CHOICES = [
        (tz, tz) for tz in common_timezones if tz.startswith('US/')]

    username = models.TextField(_('username'), unique=True, max_length=200)
    email = models.EmailField(
        _('Notification Email'),
        help_text="The email account notifications are sent to. This will"
                  " not change the email address you use to login.",
        unique=True
    )
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_active = models.BooleanField(_('active'), default=True)
    date_joined = models.DateTimeField(_('date joined'), default=now)
    modified_at = models.DateTimeField(auto_now=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    biography = models.TextField(blank=True)
    image = models.ForeignKey(
        Image, blank=True, null=True, related_name='profile_image')
    timezone = models.CharField(
        max_length=255, default="US/Central", choices=TIMEZONE_CHOICES)
    uuid = UUIDField(version=4, editable=False)
    unsubscribed = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    group_notification_period = models.CharField(
        _('Default Notification Setting'),
        choices=NOTIFICATION_PERIODS, max_length=50, default='immediate')
    direct_notification_period = models.CharField(
        choices=NOTIFICATION_PERIODS, max_length=50, default='immediate')
    moderator_notification_period = models.IntegerField(
        _('Moderation Notification Time Period'),
        help_text=("Minimum time between notifications of new messages to"
                   " moderate"),
        choices=MODERATION_NOTIFICATION_PERIODS, default=1)
    phone = models.CharField(max_length=30, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    state = models.CharField(
        max_length=2, blank=True, choices=[(state, state) for state in STATES])
    facebook_url = models.URLField(blank=True)
    twitter_handle = models.CharField(
        blank=True, max_length=20, validators=[validate_twitter_handle])
    website_url = models.URLField(blank=True)
    invite_verified = models.BooleanField(default=True)
    show_groups_on_profile = models.BooleanField(
        default=True,
        help_text=u'Can we display the groups you'
                  u' belong to on your public profile?'
    )
    tos_accepted_at = models.DateTimeField(blank=True, null=True)
    ucoc_accepted_at = models.DateTimeField(blank=True, null=True)
    has_viewed_tutorial = models.BooleanField(default=False)
    # pylint: disable=invalid-name
    receive_group_join_notifications = models.BooleanField(
        default=True,
        help_text=u'Would you like to receive notifications when new users'
                  u' join your groups?'
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'

    class Meta(object):
        """Meta options."""
        verbose_name = _('user')
        verbose_name_plural = _('users')
        permissions = (
            ('can_view_banned', 'Can view banned users.'),
            ('can_ban', 'Can ban users.'),
            ('can_unban', 'Can unban users.'),
            ('can_view_user_report', 'Can view user report.'),
            ('can_view_group_report', 'Can view group report.'),
            ('can_impersonate', 'Can impersonate other users.'),
            ('can_moderate_all_messages', 'Can moderate all messages.'),
            ('can_initiate_direct_messages', 'Can initiate direct messages.'),
            ('can_modify_permissions', 'Can modify user permissions.'),
            ('can_modify_staff_status', "Can modify a user's staff status")
        )

    def get_absolute_url(self):
        """Returns the absolute url to a user."""
        return reverse_lazy('user_details', args=[self.uuid])

    def __unicode__(self):
        """Unicode representation of a user instance."""
        return self.get_full_name()

    def save(self, *args, **kwargs):
        """Save method for User model"""
        # Lowercase all emails
        self.email = self.email.lower()
        return super(User, self).save(*args, **kwargs)

    def get_full_name(self):
        """Returns the first name and last initial or first part of email."""
        if self.system_user:
            return settings.SYSTEM_USER_NAME
        elif self.first_name and self.last_name:
            return u'%s %s.' % (self.first_name, self.last_name[:1])
        else:
            return self.get_short_name()

    def get_short_name(self):
        """Returns the first name or first part of the email."""
        if self.first_name:
            return u'%s' % self.first_name
        else:
            return u'%s' % self.email.split('@')[0]

    def get_real_name(self):
        """Gets the real full name."""
        if self.system_user:
            return settings.SYSTEM_USER_NAME
        elif self.first_name and self.last_name:
            return u'{first_name} {last_name}'.format(
                first_name=self.first_name, last_name=self.last_name)
        else:
            return self.get_short_name()

    @property
    def full_url(self):
        """The URL (including the origin) of the user profile page"""
        return settings.ORIGIN + reverse('user_details', args=[self.uuid])

    def group_join_requests_to_moderate(self):
        """Returns a list of group join requests for the user to moderate."""
        return self.grouprequest_set.unapproved().filter(group__owners=self)

    def has_group_join_requests_to_moderate(self):
        """Boolean indicating if user has group join requests to moderate."""
        return self.group_join_requests_to_moderate().exists()

    @property
    def messages_to_moderate(self):
        """Returns a list of messages for the user to moderate."""
        # This will need to be changed once 3rd parties can run groups
        queryset = Message.objects.filter(status__in=['pending', 'flagged'])

        # A message sent from a banned user is not one that needs to be
        # moderated
        queryset = queryset.exclude(sender__is_banned=True)

        if not self.global_moderator:
            queryset = queryset.filter(
                thread__thread_type='group',
                thread__group__in=self.groups_moderating
            )

        return queryset

    @property
    def global_moderator(self):
        """Return true if the user can moderate all messages"""
        if (self.is_superuser or
                self.has_perm('accounts.can_moderate_all_messages')):
            return True
        return False

    def has_messages_to_moderate(self):
        """Boolean indicating if user has messages to moderate."""
        return self.messages_to_moderate.exists()

    def get_moderation_tasks(self):
        """Gets a list of moderation task types that are pending."""
        messages_key = '%s_messages_to_mod' % self.pk
        groups_key = '%s_groups_to_mod' % self.pk
        mods = cache.get_many([messages_key, groups_key])
        if messages_key not in mods:
            messages_to_moderate = self.messages_to_moderate.count()
            cache.set(messages_key, messages_to_moderate, 600)
            mods[messages_key] = messages_to_moderate
        if groups_key not in mods:
            groups_to_moderate = self.group_join_requests_to_moderate().count()
            cache.set(groups_key, groups_to_moderate, 600)
            mods[groups_key] = groups_to_moderate
        return {
            'groups_to_mod': mods[groups_key],
            'messages_to_mod': mods[messages_key]
        }

    def is_moderator(self):
        """Returns True if user is a moderator."""
        key = self.cache_key + 'is_moderator'
        is_mod = cache.get(key)
        if is_mod is None:
            is_mod = self.groups_moderating.exists()
            cache.set(key, is_mod, 3600)
        return is_mod

    @property
    def groups_moderating(self):
        """Groups a user can moderate."""
        owned_groups = cache.get(self.cache_key + 'owned_groups')
        if owned_groups is None:
            owned_groups = self.owned_groups_set.all()
            # Cache owned groups for 1 week
            cache.set(
                self.cache_key + 'owned_groups', owned_groups, 7*24*60*60)
        return owned_groups

    @property
    def groups_joined(self):
        """Groups a user is a member of."""
        groups = cache.get(self.cache_key + 'groups_joined')
        if groups is None:
            groups = Group.objects.filter(group__user__id=self.pk)

            # Include the `Image` and `AuthGroup` models and tags
            groups = groups.select_related(
                'image', 'group', 'category').prefetch_related(
                    'tagged_items__tag')

            # Cache groups joined for 1 week
            cache.set(self.cache_key + 'groups_joined', groups, 7*24*60*60)
        return groups

    @property
    def cached_groups_joined(self):
        """Same as groups_joined, but cached on the object instance."""
        if not hasattr(self, '_cached_groups_joined'):
            # pylint: disable=attribute-defined-outside-init
            self._cached_groups_joined = self.groups_joined
        return self._cached_groups_joined

    @property
    def group_categories(self):
        """The categories a user is interested based on groups they're in."""
        categories = set()
        for group in self.cached_groups_joined:
            categories.add(group.category.name)
        return categories

    @property
    def messagable_groups(self):
        """Groups a user can send a message to."""
        if self.is_superuser:
            return Group.objects.all()
        else:
            return self.groups_joined

    @property
    def can_moderate(self):
        """Boolean indicating whether user has permission to moderate."""
        if self.global_moderator:
            return True
        elif self.groups_moderating.exists():
            return True
        else:
            return False

    @property
    def can_flag_messages(self):
        """Is this user allowed to flag messages?"""
        return self.is_banned is False

    @property
    def all_user_messageable(self):
        """Boolean indicating if all users can direct message this user"""
        if self.is_staff:
            return True
        elif self.can_moderate:
            return True
        else:
            return False

    def can_direct_message_user(self, user):
        """Return true if user is allowed to direct message to a user"""
        if user == self:
            # Users should never be able to message themselves
            return False

        if self.system_user:
            # The system user must always be able to create direct messages
            return True
        elif self.is_staff:
            # Staff can initiate direct messages with users
            return True
        elif user.all_user_messageable:
            # If the end-user is always allowed to receive messages, allow the
            # new direct message to go through
            return True
        elif self.has_perm('accounts.can_initiate_direct_messages'):
            # If this user has the specific permission of being able to direct
            # message users, allow this user to go through. Superuers will
            # always have this permission.
            return True

        # If the user is not allowed to direct message the requested user
        # return false
        return False

    @property
    def system_user(self):
        """Boolean indicating whether the user is the 'system user'"""
        if self.email == settings.SYSTEM_USER_EMAIL:
            return True
        else:
            return False

    @property
    def private_hash(self):
        """
        A URL-safe string that is unique to the user's email address
        which will allow them to access the app without logging in
        """
        # Generate a hex version of our app's secret key and user's email
        return generate_nologin_hash(self.email.lower())

    @property
    def unsubscribe_url(self):
        """URL the user visits to unsubscribe from all emails"""
        return unsubscribe_url(self.email)

    @property
    def change_notification_url(self):
        """URL the user visits to change notification preferences"""
        origin = settings.ORIGIN
        path = reverse(
            'logged_out_update_subscription',
            args=[self.pk, self.private_hash]
        )
        return "{}{}".format(origin, path)

    def can_send_to_group(self, group):
        """Boolean indicating if a user has permission to send to a group."""
        if not group:
            # This is a DM
            return True
        if self.is_superuser:
            return True
        elif group in self.groups_moderating:
            return True
        elif group in self.groups_joined and not group.moderated:
            return True
        elif group.whitelist_users.filter(pk=self.pk).exists():
            # User is whitelisted to send to this group
            return True
        elif group in self.groups_joined:
            return False
        else:
            raise PermissionDeniedError(
                "User Not Allowed To Post To Group %s" % group.group.name)

    def request_to_join_group(self, group):
        """Creates a new request to join a group.

        Returns the request object.
        """
        request, created = GroupRequest.objects.get_or_create(
            user_id=self.pk, group=group, approved=None)
        if created:
            group_tasks.notify_owners_of_group_request.delay(request.pk)
        return request

    def add_to_group(
            self, group_id, notification=None, period=None, immediate=False):
        """Adds the user to a group.

        Optionally provide kwargs, which will be passed into the subscription
        create statement
        """
        if immediate:
            group_tasks.add_user_to_group(
                user_id=self.pk,
                group_id=group_id,
                notification=notification,
                period=period
            )
        else:
            group_tasks.add_user_to_group.delay(
                user_id=self.pk,
                group_id=group_id,
                notification=notification,
                period=period
            )

    def remove_from_group(self, group):
        """Removes user from a group and handles existing threads/messages."""
        group_tasks.remove_user_from_group(user=self, group=group)

    def bulk_unsubscribe(self):
        """Unsubscribe from all group notifications for user"""
        return self.subscriptions.update(period='none')

    def can_view_profile(self, user):
        """Determine if this user can view the specified user's profile."""
        if user == self:
            return True
        elif not user.is_banned:
            return True
        elif self.has_perm('accounts.can_view_banned'):
            return True
        elif self.is_superuser:
            return True
        return False

    def can_impersonate(self):
        """Determines if a user can impersonate another user."""
        has_perm = self.has_perm('accounts.can_impersonate')
        return has_perm or self.is_superuser

    def direct_messages_sent_since(self, since_datetime=None):
        """Returns count of messages sent by the user since since_datetime.

        since_datetime defaults to 24 hours.
        """
        if not since_datetime:
            since_datetime = now() - timedelta(hours=24)
        count = Message.objects.filter(
            sender=self, created_at__gte=since_datetime).count()
        return count


class UserAutocomplete(autocomplete_light.AutocompleteModelBase):
    """Creates an autocomplete endpoint for searching users."""
    search_fields = ['^first_name', 'last_name', 'email']

    def choices_for_request(self):
        """Autocomplete choices for request"""
        user = self.request.user
        # Only allow staff or superusers to view this list.
        if user.is_superuser or user.is_staff:
            return super(UserAutocomplete, self).choices_for_request()
        return []

    # pylint: disable=interface-not-implemented,no-self-use
    def choice_label(self, choice):
        """Autocomplete choice labels"""
        if choice.last_name:
            return u'%s %s (%s)' % (
                choice.first_name, choice.last_name, choice.email)
        else:
            return u'%s (%s)' % (choice.first_name, choice.email)

autocomplete_light.register(User, UserAutocomplete)


def generate_unique_invite_code():
    """Generate a unique invite code."""
    code = uuid4().get_hex()
    # Should be absolutely unnecessary but just in case
    while Invite.objects.filter(code=code).exists():
        code = uuid4().get_hex()
    return code


class Invite(TimestampModel):
    """Model for storing user invites."""
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, blank=True)
    created_by = models.ForeignKey(User)
    consumed_at = models.DateTimeField(null=True, blank=True)
    notified = models.DateTimeField(null=True, editable=False)
    code = models.CharField(max_length=32, default=generate_unique_invite_code)
    consumed_by = models.ForeignKey(
        User, blank=True, null=True, related_name='consumed_invite')

    class Meta(object):
        """Meta options for Invite Model"""
        permissions = (
            ("email_invites", "Email Invites To Users"),
        )
        get_latest_by = 'created_at'

    def clean(self):
        """Clean model before saving._

        Email address is converted to lowercase.
        """
        self.email = self.email.lower()
        return super(Invite, self).clean()

    def send_invite(self, sender_id=None):
        """Send an invite to the user"""
        # Bail out if we've already sent the invite
        if self.notified:
            return None

        # If a sender was not passed
        if not sender_id:
            sender = self.created_by
        else:
            sender = User.objects.get(pk=sender_id)

        # If the user doesn't have permission to email invites
        # bail out.
        if (not sender.has_perm('accounts.email_invites')
                and not sender.is_superuser):
            return None

        render_and_send_invite_email.delay(self.pk)

    def use_invite(self, user_id):
        """Consume the invite and update a user."""
        user = User.objects.get(pk=user_id)
        user.invite_verified = True
        user.is_staff = self.is_staff
        user.is_superuser = self.is_superuser
        for group in self.groups.all():
            user.add_to_group(group.pk)
        user.save()
        self.consumed_at = now()
        self.consumed_by = user
        self.save()
        return user


class Visit(TimestampModel):
    """Store information about a user's visits to the site."""
    user = models.ForeignKey(User, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
