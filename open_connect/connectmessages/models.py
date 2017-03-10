"""Models related to sending messages."""
# pylint: disable=no-init
from bs4 import BeautifulSoup
from datetime import timedelta
import logging
import re

from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import models
from django.db.models import Q, ObjectDoesNotExist
from django.utils.encoding import smart_text
from django.utils.timezone import now
from unidecode import unidecode
import pytz

from open_connect.media.models import Image, ShortenedURL
from open_connect.notifications.models import Subscription
from open_connect.connectmessages import tasks

from open_connect.connect_core.utils.models import TimestampModel
from open_connect.connect_core.utils.stringhelp import unicode_or_empty


LOGGER = logging.getLogger('connectmessages.models')


USERTHREAD_STATUSES = (
    ('active', 'Active'),
    ('archived', 'Archived'),
    ('deleted', 'Deleted')
)

THREAD_TYPES = (
    ('direct', 'Direct Message'),
    ('group', 'Group Message')
)

THREAD_STATUSES = (
    ('active', 'Active'),
    ('deleted', 'Deleted')
)

MESSAGE_STATUSES = (
    ('approved', 'Approved'),
    ('flagged', 'Flagged'),
    ('spam', 'Spam'),
    ('pending', 'Pending Moderator Approval'),
    ('vetoed', 'Vetoed'),
    ('deleted', 'Deleted')
)

# Messages with these statuses will be visible to normal users. Any other
# status will remove a message from view except for cases where a user
# has been granted specific permission to view the message.
VISIBLE_MESSAGE_STATUSES = ('approved', 'flagged')

# Regex from http://stackoverflow.com/a/499371/379236
URL_RE = re.compile(ur'(?u)href=[\'"]?([^\'" >]+)')

# Regex from http://stackoverflow.com/a/12863279/1588398
STRIP_RE = re.compile(ur'^[^a-zA-z]*|[^a-zA-Z]*$')


class DeletedItemsManager(models.Manager):
    """Default manager for messages. Hides messages marked as deleted."""
    def get_queryset(self):
        """Returns queryset with deleted messages excluded."""
        return super(DeletedItemsManager, self).get_queryset().exclude(
            status='deleted'
        )

    def with_deleted(self):
        """Returns queryset that includes deleted messages."""
        return super(DeletedItemsManager, self).get_queryset()


class UserThread(TimestampModel):
    """Store additional information on relationship between thread and user."""
    thread = models.ForeignKey('Thread')
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    read = models.BooleanField(
        default=False,
        verbose_name=u'Thread Read',
        db_index=True
    )
    last_read_at = models.DateTimeField(blank=True, null=True)
    subscribed_email = models.BooleanField(
        default=True,
        verbose_name=u'Subscribed for Email',
        help_text='Subscribed to receive new message alerts via email')
    status = models.CharField(
        max_length=50,
        default='active',
        choices=USERTHREAD_STATUSES,
        db_index=True
    )

    objects = DeletedItemsManager()

    class Meta(object):
        """Meta options for UserThread."""
        index_together = [
            ["user", "read"],
            ["thread", "subscribed_email"]
        ]
        unique_together = ("thread", "user")

    def delete(self, using=None):
        """Overrides delete so we don't actually delete."""
        self.status = 'deleted'
        self.save()
        LOGGER.debug('UserThread %s deleted.', self.pk)

    def archive(self):
        """Archives the current UserThread."""
        self.status = 'archived'
        self.save()


class ThreadPublicManager(DeletedItemsManager):
    """Manager for accessing messages that are visible."""
    def get_queryset(self):
        """Default queryset for this manager - gets visible threads."""
        return super(ThreadPublicManager, self).get_queryset().filter(
            visible=True,
            total_messages__gt=0,
        ).exclude(
            first_message__isnull=True
        ).select_related(
            'first_message', 'first_message__sender',
            'latest_message', 'latest_message__sender',
            'group', 'group__group'
        ).defer(
            'first_message__sender__biography',
            'latest_message__sender__biography',
            'group__description')

    def by_group(self, group, queryset=None):
        """Get threads that any user can view for a single group."""
        if queryset is None:
            queryset = self.get_queryset()
        queryset = queryset.filter(
            first_message__sender__is_banned=False,
            group=group,
            group__private=False
        )
        return queryset

    def by_user(self, user, queryset=None):
        """Get threads where the user is a recipient."""
        if queryset is None:
            queryset = self.get_queryset()
        queryset = queryset.filter(
            Q(first_message__sender__is_banned=False)
            | Q(first_message__sender=user),
            recipients=user,
        ).extra(
            select={
                'read': 'connectmessages_userthread.read',
                'last_read_at': 'connectmessages_userthread.last_read_at',
                'userthread_status': 'connectmessages_userthread.status'
            },
            where=[
                "connectmessages_userthread.status != 'deleted'"
            ]
        ).select_related(
            'group__group', 'first_message__sender', 'latest_message__sender'
        ).defer(
            'group__description',
            'first_message__sender__biography',
            'latest_message__sender__biography',
        )
        return queryset

    def get_by_user(self, thread_id, user, queryset=None):
        """Gets a thread for a user if they have permission to access it."""
        if queryset == None:
            queryset = self.get_queryset()
        thread = queryset.get(pk=thread_id)

        # Use the thread's `visible_to_user()` method to determine if the user
        # can see the thread.
        if thread.visible_to_user(user):
            return thread

        # User doesn't have permission, raise exception
        raise ObjectDoesNotExist


class Thread(TimestampModel):
    """Model for tying related messages together."""
    subject = models.CharField(max_length=255)
    thread_type = models.CharField(
        blank=False, choices=THREAD_TYPES, max_length=50, default='group')
    group = models.ForeignKey('groups.Group', null=True)
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, through='UserThread')
    first_message = models.ForeignKey(
        'Message', null=True, blank=True, related_name='message_threadstarter')
    latest_message = models.ForeignKey(
        'Message', null=True, blank=True, related_name='message_latestinthread')
    total_messages = models.IntegerField(default=1)
    visible = models.BooleanField(
        default=True, db_index=True, verbose_name=u'Visible to users')
    closed = models.BooleanField(
        default=False, verbose_name=u'Closed to new comments')
    status = models.CharField(
        max_length=50,
        default='active',
        choices=THREAD_STATUSES,
        db_index=True
    )

    objects = DeletedItemsManager()
    public = ThreadPublicManager()

    class Meta(object):
        """Meta options for Thread."""
        ordering = ['-latest_message__created_at']

    def __unicode__(self):
        """Return object's unicode representation."""
        return "Thread %s" % self.subject

    @property
    def is_system_thread(self):
        """Returns true if this is a thread started by the system message"""
        return self.first_message.is_system_message

    def get_absolute_url(self):
        """Return absolute URL for a thread"""
        return reverse('thread', args=(self.pk,))

    def get_unsubscribe_url(self):
        """Return the URL of the unsubscribe view"""
        return reverse('thread_unsubscribe', args=(self.pk,))

    def add_user_to_thread(self, user):
        """Add a user to a thread."""
        defaults = {}
        if self.thread_type == 'group':
            # This is put inside a try/except because it is possible for staff
            # to send messages to groups they are not members of and thus
            # do not have a subscription to.
            try:
                subscription = Subscription.objects.get(
                    user=user, group=self.group)

                # By default everyone is subscribed to new threads
                # If this user has determined to not subscribe, unmark them
                if subscription.period == 'none':
                    defaults['subscribed_email'] = False
            except Subscription.DoesNotExist:
                defaults['subscribed_email'] = False

        UserThread.objects.get_or_create(
            thread_id=self.pk, user=user, defaults=defaults)

    def serializable(self, timezone=None):
        """Returns a serializable version of the Thread model"""

        # We cannot do `serializable(self, timezone=None):` because tests need
        # to be able to ovveride the time zone
        if timezone is None:
            timezone = settings.TIME_ZONE

        zone = pytz.timezone(timezone)

        if self.group:
            category = self.group.category.slug
            group_url = reverse('group_details', kwargs={'pk': self.group.pk})
            reply_url = reverse('create_reply', args=[self.pk])
            group_id = self.group.pk
        else:
            category = None
            group_url = ''
            reply_url = reverse('create_direct_message_reply', args=[self.pk])
            group_id = None

        if not self.group and not self.is_system_thread:
            recipients = self.recipients.all()
        else:
            recipients = None

        if getattr(self, 'read', None):
            unread_messages = 0
        elif getattr(self, 'last_read_at', None):
            last_read_at = (self.last_read_at.astimezone(zone))
            unread_messages = self.message_set.filter(
                created_at__gt=last_read_at).count()
        else:
            unread_messages = self.total_messages

        response = {
            'id': self.pk,
            'total_messages': str(self.total_messages),
            'subject': unicode(self.subject),
            'snippet': unicode(self.first_message.snippet),
            'latest_message_at': str(
                self.latest_message.created_at.astimezone(zone)),
            'json_url': str(reverse('thread_details_json', args=[self.pk])),
            'reply_url': reply_url,
            'unsubscribe_url': self.get_unsubscribe_url(),
            'read': getattr(self, 'read', None),
            'group': unicode_or_empty(self.group),
            'group_url': group_url,
            'group_id': group_id,
            'type': str(self.thread_type),
            'category': unicode_or_empty(category),
            'unread_messages': unread_messages,
            'is_system_thread': self.is_system_thread,
            'userthread_status': getattr(self, 'userthread_status', None)
        }

        if recipients:
            response['recipients'] = [
                str(recipient) for recipient in recipients
            ]

        return response

    def messages_for_user(self, user):
        """Gets messages for a user."""
        connectmessages = Message.objects.select_related(
            'sender', 'thread', 'thread__group', 'thread__group__group',
            'thread__first_message__sender').filter(
                thread_id=self.pk)
        permitted_messages = []
        for message in connectmessages:
            if message.visible_to_user(user):
                if getattr(self, 'read', False):
                    message.read = True
                elif getattr(self, 'last_read_at', False):
                    message.read = message.created_at < self.last_read_at
                else:
                    message.read = False
                permitted_messages.append(message)
        return permitted_messages

    # pylint: disable=too-many-return-statements
    def visible_to_user(self, user, message=None):
        """Returns True if a thread is visible to a user"""
        # Superusers should see everything
        if user.is_superuser:
            return True

        # A deleted thread is never allowed
        if self.status == 'deleted':
            return False

        # Check to see if the first message was sent by a banned and
        # disallow it if the user is banned
        if (self.first_message.sender.is_banned and
                self.first_message.sender != user):
            return False

        if not getattr(self.group, 'private', False):
            return True

        # By default the user is not a recipient of the message
        is_recipient = False

        # Check to see if our `Message` object has `is_recipient` and
        # that attribute is true, otherwise query to see if the user
        # has a UserThread record associated with the Thread
        if hasattr(message, 'is_recipient'):
            is_recipient = message.is_recipient
        else:
            is_recipient = self.recipients.filter(pk=user.pk).exists()

        if is_recipient:
            return True

        # Check to see if the group is one that the user is moderating
        if self.group and user.groups_moderating.filter(
                pk=self.group.pk).exists():
            return True

        # Default to false
        return False


class MessagePublicManager(DeletedItemsManager):
    """Manager for accessing messages that are visible."""
    def get_queryset(self):
        """Default queryset for this manager - gets visible threads."""
        return super(MessagePublicManager, self).get_queryset().filter(
            thread__visible=True, status__in=VISIBLE_MESSAGE_STATUSES)


class Message(TimestampModel):
    """Message model."""
    sender = models.ForeignKey(settings.AUTH_USER_MODEL)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    thread = models.ForeignKey(Thread, blank=True)
    text = models.TextField()
    clean_text = models.TextField(blank=True)
    status = models.CharField(
        choices=MESSAGE_STATUSES,
        default='pending',
        db_index=True,
        max_length=50
    )
    sent = models.BooleanField(default=False)
    wiped = models.BooleanField(default=False)
    images = models.ManyToManyField(Image, blank=True)
    links = models.ManyToManyField(ShortenedURL, blank=True)
    flags = models.ManyToManyField('moderation.Flag', blank=True)

    objects = DeletedItemsManager()
    public = MessagePublicManager()

    class Meta(object):
        """Meta options for Message."""
        get_latest_by = 'created_at'
        ordering = ['-created_at']

    def __unicode__(self):
        """Unicode representation of the message instance."""
        return "Message %s" % unicode(self.pk)

    @property
    def is_system_message(self):
        """Returns True if this is a system message (sent by a system user)"""
        return self.sender.system_user

    def save(self, **kwargs):
        """Save a message."""
        self.clean_text = self._text_cleaner()

        shorten = kwargs.pop('shorten', True)

        if not self.pk:
            created = True
            self.status = self.get_initial_status()
        else:
            created = False

        # Save the model
        result = super(Message, self).save(**kwargs)

        if shorten:
            # Rewrite urls for tracking
            self._shorten()

        if created:
            # These fields need to be set immediately or things break.
            if self.thread.first_message is None:
                self.thread.first_message = self
                self.thread.latest_message = self

            self.thread.save()

            self.thread.add_user_to_thread(self.sender)

            if self.status == 'approved':
                tasks.send_message(self.pk, False)

        return result

    def delete(self, using=None):
        """Marks a message as deleted."""
        self.status = 'deleted'
        self.save()
        thread = self.thread
        thread.total_messages -= 1
        if thread.total_messages:
            if thread.first_message_id == self.pk:
                thread.first_message = thread.message_set.all()[0]
            if thread.latest_message_id == self.pk:
                thread.latest_message = thread.message_set.all().reverse()[0]
        else:
            thread.status = 'deleted'
        thread.save()

    def flag(self, flagged_by):
        """Method to flag a message"""
        # Fail silently if user can't flag messages
        if not flagged_by.can_flag_messages:
            return

        self.flags.create(flagged_by=flagged_by)
        self.status = 'flagged'
        self.save()

    def _shorten(self):
        """Replaces urls in message with redirect url."""
        def create_shortened_urls(matches):
            """Helper function for "shortening" urls."""
            for match in set(matches.groups()):
                # If this is not an http/s link, ignore it
                if not match.startswith('http'):
                    return 'href="{url}"'.format(url=match)
                try:
                    shortened_url, _ = ShortenedURL.objects.get_or_create(
                        url=match)
                except ShortenedURL.MultipleObjectsReturned:
                    shortened_url = ShortenedURL.objects.filter(
                        url=match).latest()
                self.links.add(shortened_url)
                shortened_url.message_count += 1
                shortened_url.save()
                # Rewrite the url with a data-redirect url pointing to our
                # redirect. This will be copied to the href attribute after
                # oembeds are created on the page.
                url = u'href="%s" data-redirect="%s' % (
                    shortened_url.url, shortened_url.get_absolute_url())
                return url

        self.text, count = URL_RE.subn(
            create_shortened_urls, smart_text(self.text))
        if count:
            self.save(shorten=False)

    def get_absolute_url(self):
        """Returns the absolute URL for an individual message."""
        return self.thread.get_absolute_url()

    def get_initial_status(self):
        """Returns the initial status of the message when created"""
        yesterday = now() - timedelta(hours=24)

        if self.is_system_message:
            # If a system message auto-approve
            status = 'approved'

        elif self.sender.is_superuser:
            # If sender is a superuser, auto-approve
            status = 'approved'

        elif (self.thread.thread_type == 'group' and
              self.sender.can_send_to_group(self.thread.group)):
            # If a group message and the sender can send to a group, approve
            status = 'approved'

        elif (self.thread.thread_type == 'direct' and
              self.sender.direct_messages_sent_since(yesterday) <= 10):
            # Up to 10 DMs per day may be sent without moderation
            status = 'approved'

        else:
            # All other messages are pending by default
            status = 'pending'

        return status

    def serializable(self, timezone=None):
        """Return a serializable representation of the message."""

        # We cannot do `serializable(self, timezone=None):` because tests need
        # to be able to ovveride the time zone
        if timezone is None:
            timezone = settings.TIME_ZONE

        zone = pytz.timezone(timezone)

        return {
            'id': self.pk,
            'sent_at': str(self.created_at.astimezone(zone)),
            'sender': {
                'sender': str(self.sender),
                'sender_is_staff': self.sender.is_staff,
                'sender_url': reverse(
                    'user_details', kwargs={'user_uuid': self.sender.uuid}),
            },
            'group': unicode_or_empty(self.thread.group),
            'snippet': self.snippet,
            'text': self.text,
            'reply_url': reverse('create_reply', args=[self.thread_id]),
            'flag_url': reverse(
                'flag_message', kwargs={'message_id': self.pk}
            ),
            'read': getattr(self, 'read', None),
            'is_system_message': self.is_system_message,
            'pending': (self.status == 'pending')
        }

    def _text_cleaner(self):
        """Removes HTML from the text."""
        # Insert the raw message into BeautifulSoup
        soup = BeautifulSoup(self.text, "lxml")

        # Extract the clean text BeautifulSoup found in the message.
        text = soup.text

        # Turn newlines into white spaces
        text = " ".join(line.strip() for line in text.split("\n"))

        return text

    @property
    def long_snippet(self):
        """Return the first 140 characters of clean_text."""
        return self.clean_text[:140]

    @property
    def snippet(self):
        """Return the first 24 ascii characters of the non-HTML message."""
        if len(self.long_snippet) <= 24:
            # If the message is unusually short, convert to ASCII and strip
            # all non-letters
            return STRIP_RE.sub('', unidecode(self.long_snippet)[:24])
        else:
            # We'll grab the first 30 characters incase there are spaces or
            # weird characters near the end
            raw_snippet = self.long_snippet[:30]

            # We'll replace non-ASCII characters and strip non-letter
            # characters
            clean_snippet = STRIP_RE.sub('', unidecode(raw_snippet)[:21])

            # We'll return the first 21 characters plus an ASCII elipsis
            return clean_snippet[:21] + '...'

    # pylint: disable=too-many-return-statements
    def visible_to_user(self, user):
        """Returns True if a user can view message. False if user can't."""
        # If the user is a superuser, stop all tests and return True
        if user.is_superuser:
            return True

        # If the message itself is deleted or vetoed, return False
        if self.status in ['deleted', 'vetoed']:
            return False

        # If the user sent the message, return the message
        if self.sender == user:
            return True

        # If the sender is banned, return False. Because this is located after
        # the "Return True if message is from sender" this will allow us to
        # "shadow ban" users.
        if self.sender.is_banned == True:
            return False

        if not self.thread.visible_to_user(user, self):
            return False

        # If the thread is visible and the message is approved, go for it
        if self.status == 'approved':
            return True

        # Unapproved messages should be visible to moderators
        if (user.global_moderator or
                self.thread.group in user.groups_moderating):
            return True

        # By default a message shouldn't be available
        return False


class ImageAttachment(models.Model):
    """Model for storing images with messages."""
    message = models.ForeignKey(Message)
    image = models.ForeignKey(Image)

    def __unicode__(self):
        return u'Image for %s' % self.message.thread.subject
