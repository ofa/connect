"""Celery tasks for notifications app."""
# pylint: disable=not-callable
from datetime import timedelta
from email.utils import formataddr
import logging

from celery import shared_task
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from django.utils.translation import ngettext
from django.template.loader import render_to_string

from open_connect.mailer.utils import send_email
from open_connect.notifications.models import Notification


LOGGER = logging.getLogger('notifications.tasks')


@shared_task()
def create_group_notifications(message_id):
    """Create notifications for messages sent to a group."""
    # Import here to avoid circular import
    from open_connect.connectmessages.models import Message, UserThread
    message = Message.objects.get(pk=message_id)
    userthreads = UserThread.objects.filter(
        thread_id=message.thread_id,
        subscribed_email=True,
        user__unsubscribed=False
    ).exclude(
        user_id=message.sender_id
    )

    # User.objects.filter(userthread__thread=message.thread)
    for userthread in userthreads:
        create_group_notification.delay(message.pk, userthread.pk)


@shared_task()
def create_group_notification(message_id, userthread_id):
    """Create a notification for a specific user"""
    # Import here to avoid circular import
    from open_connect.connectmessages.models import Message, UserThread
    message = Message.objects.select_related('thread').get(pk=message_id)
    userthread = UserThread.objects.select_related('user').extra(
        select={
            'subscription_id': 'notifications_subscription.id',
            'subscription_period': 'notifications_subscription.period'
        },
        tables=['notifications_subscription'],
        where=[
            'notifications_subscription.user_id=accounts_user.id',
            'notifications_subscription.group_id=%s'
        ],
        params=[message.thread.group_id]
    ).get(id=userthread_id)

    try:
        notification = Notification.objects.create(
            recipient_id=userthread.user.pk,
            subscription_id=userthread.subscription_id,
            message=message,
            triggered_at=message.created_at
        )

        if userthread.subscription_period == 'immediate':
            send_immediate_notification.delay(notification.pk)
    except IntegrityError as exception:
        LOGGER.error(
            'Create Group Notification ' + exception.__cause__)


@shared_task()
def create_recipient_notifications(message_id):
    """Create notifications for messages sent to an individual."""
    # Import here to avoid circular import
    from open_connect.connectmessages.models import Message
    message = Message.objects.get(pk=message_id)
    for recipient in message.thread.recipients.exclude(
            pk=message.sender.pk).exclude(unsubscribed=True):
        try:
            notification = Notification.objects.create(
                recipient_id=recipient.pk,
                message=message,
                triggered_at=message.created_at
            )
            if recipient.direct_notification_period == 'immediate':
                send_immediate_notification.delay(notification.pk)
        except IntegrityError as exception:
            LOGGER.error(
                'Create Recipient Notification ' + exception.__cause__)


@shared_task()
def send_immediate_notification(notification_id):
    """Send an email for a given notification."""
    notification = Notification.objects.select_related(
        'recipient', 'message', 'message__thread').get(pk=notification_id)
    recipient = notification.recipient
    message = notification.message
    context = {
        'notification': notification,
        'message': message,
        'recipient': recipient,
        'email': recipient.email
    }
    text = render_to_string(
        'notifications/email/email_immediate.txt', context)
    html = render_to_string(
        'notifications/email/email_immediate.html', context)

    # Determine the correct format of the subject line of the notification
    if message.thread.thread_type == 'direct':
        subject_format = u"{subject}"
    else:
        subject_format = u"[{group}] {subject}"
    subject = subject_format.format(
        group=message.thread.group, subject=message.thread.subject)

    if message.sender.is_staff:
        from_name = u'{name}, Staff Member, {brand}'.format(
            name=message.sender.get_full_name(),
            brand=settings.BRAND_TITLE)
    else:
        from_name = u'{name}, {brand}'.format(
            name=message.sender.get_full_name(),
            brand=settings.BRAND_TITLE)
    from_email = formataddr((from_name, settings.DEFAULT_FROM_ADDRESS))

    to_email_tup = (recipient.get_full_name(), notification.recipient.email)
    to_address = formataddr(to_email_tup)

    send_email(
        email=to_address,
        from_email=from_email,
        subject=subject,
        text=text,
        html=html
    )

    notification.consumed_at = now()
    notification.save()


@shared_task()
def send_digest_notification(user_id):
    """Send a digest notification for an individual user"""
    notifications = Notification.objects.select_related('recipient').filter(
        recipient_id=user_id,
        consumed_at__isnull=True,
        # Only send notifications for approved messages, otherwise leave the
        # messages pending
        message__status='approved'
    ).exclude(subscription__period__in=['immediate', 'none']).order_by(
        '-message__thread', '-message__pk')
    if not notifications:
        return
    recipient = notifications[0].recipient

    context = {
        'notifications': notifications,
        'recipient': recipient,
        'email': recipient.email
    }
    text = render_to_string('notifications/email/email_digest.txt', context)
    html = render_to_string('notifications/email/email_digest.html', context)

    subject = u'Your {brand} {day} Digest - {num} New {word}'.format(
        brand=settings.BRAND_TITLE,
        day=now().strftime('%A'),
        num=notifications.count(),
        word=ngettext('Message', 'Messages', notifications.count())
    )

    send_email(
        email=recipient.email,
        from_email=settings.DEFAULT_FROM_EMAIL,
        subject=subject,
        text=text,
        html=html
    )

    notifications.update(consumed_at=now())


@shared_task()
def send_daily_email_notifications():
    """Sends emails for subscriptions that are daily digests."""
    daily_notifications = Notification.objects.filter(
        subscription__period='daily',
        queued_at__isnull=True,
        # Only send notifications for approved messages, otherwise leave the
        # messages pending
        message__status='approved'
    )

    # Grab the unique user id of each user with a daily notification.
    users_with_notifications_lazy = daily_notifications.distinct(
        "recipient").values_list("recipient_id", flat=True)

    # We have to actually execute the above "find users with notifications"
    # lookup before we do any update operatons. Thus we need to load the list
    # of users with notifications into memory. Thanfully it's just a list of
    # integers
    users_with_notifications = list(users_with_notifications_lazy)

    # Queue all the daily notifications in one big update
    daily_notifications.update(queued_at=now())

    for user_id in users_with_notifications:
        send_digest_notification.delay(user_id)


@shared_task()
def send_moderation_notification(group_owner_id, top_current_hour_iso):
    """Send an individual moderation notification"""
    from open_connect.accounts.models import User
    owner = User.objects.get(pk=group_owner_id)
    top_current_hour = parse_datetime(top_current_hour_iso)

    # Find the last time we would've used as a cut off as a message
    # moderation notification time
    notification_start = top_current_hour - timedelta(
        hours=owner.moderator_notification_period)

    # Grab all the messages that were modified before the current top hour and
    # after the last cut-off point for messages
    all_messages = owner.messages_to_moderate

    total_new_messages = all_messages.filter(
        modified_at__lt=top_current_hour,
        modified_at__gte=notification_start
    ).count()

    # We don't want to re-notify users of the same pending messages, so we need
    # to bail out here if there are no new pending messages
    if total_new_messages == 0:
        return

    # We'll include the total number of pending messages in the template
    total_messages = all_messages.count()

    context = {
        'total_messages': total_messages,
        'total_new_messages': total_new_messages,
        'recipient': owner,
        'email': owner.email
    }

    subject = u"You have {count} new {word} to moderate on Connect".format(
        count=total_new_messages,
        word=ngettext('message', 'messages', total_new_messages))
    text = render_to_string(
        'notifications/email/moderator_notification.txt', context)
    html = render_to_string(
        'notifications/email/moderator_notification.html', context)

    send_email(
        email=owner.email,
        from_email=settings.DEFAULT_FROM_EMAIL,
        subject=subject,
        text=text,
        html=html
    )


@shared_task()
def send_moderation_notifications():
    """Queue up notifications of new messages to moderate"""
    from open_connect.accounts.models import User
    # Get the top of the current hour. We use the top of the hour so we don't
    # have to worry about this task running at exactly the same time after each
    # hour.
    top_current_hour = now().replace(minute=0, second=0, microsecond=0)

    # Because we allow notification periods upto 24 hours previous, but still
    # want to limit the total number of owners checked against, we'll want to
    # exclude owners with pending messages greater than 24 hours old.
    top_hour_yesterday = top_current_hour - timedelta(days=1)

    # Get all the messages that are marked as pending that have been modified
    # previous to the current hour
    owners_with_messages = User.objects.filter(
        owned_groups_set__thread__message__status__in=['pending', 'flagged'],
        owned_groups_set__thread__message__modified_at__lt=top_current_hour,
        owned_groups_set__thread__message__modified_at__gte=top_hour_yesterday
    ).distinct().only('moderator_notification_period')

    can_moderate_all = User.objects.filter(
        Q(user_permissions__codename='can_moderate_all_messages')
        | Q(groups__permissions__codename='can_moderate_all_messages')
    )

    users_to_notify = set(list(owners_with_messages) + list(can_moderate_all))

    for user_to_notify in users_to_notify:
        time_period = user_to_notify.moderator_notification_period

        # We search for a remainder of 0 between the notification time period
        # and the current hour (which can be between 0 and 24.) This means that
        # notification time periods must ALWAYS be factors of 24 (or 0)
        if time_period != 0 and (top_current_hour.hour % time_period) == 0:
            send_moderation_notification.delay(
                user_to_notify.pk, top_current_hour.isoformat())
