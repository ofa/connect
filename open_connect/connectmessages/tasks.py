"""Celery tasks for connectmessages app."""
# pylint: disable=not-callable
from celery import shared_task
from django.conf import settings

from open_connect.notifications.tasks import (
    create_group_notifications, send_immediate_notification
)


def import_image_attachment():
    """Avoid circular dependency import error but still make this mockable."""
    from open_connect.connectmessages.models import ImageAttachment
    return ImageAttachment


@shared_task(name='process-image-attachment')
def process_image_attachment(image_id):
    """
    Run any tasks necessary to process a new/updated image attachment
    """
    image_attachment_model = import_image_attachment()
    image = image_attachment_model.objects.get(pk=image_id)
    image.create_display_size()
    image.create_thumbnail()


@shared_task(name='send-message-to-group')
def send_message(message_id, shorten=True):
    """Process a message that is sent to a group."""
    from open_connect.connectmessages.models import Message, UserThread
    from open_connect.notifications.models import Subscription

    message = Message.objects.select_related().only(
        'sender', 'thread', 'sent').get(pk=message_id)
    sender = message.sender
    thread = message.thread

    # If the sender is banned, just bail out. Their act of sending the message
    # will have already placed it in their inbox. So just mark it sent and move
    # on with life.
    if message.sender.is_banned:
        message.sent = True
        message.save()
        return None

    # Update the "total messages" count
    # This happens regardless of whether the message was already sent as
    # this moderation could be the result of reapproving a flagged message.
    approved_messages = thread.message_set.filter(status='approved')
    thread.total_messages = approved_messages.count()
    thread.latest_message = approved_messages.order_by('pk').last()
    thread.save(
        update_fields=['total_messages', 'modified_at', 'latest_message'])

    # Check to see if the message has already been sent
    if message.sent is True:
        return None

    # See if this is a new group message
    if thread.thread_type == 'group' and thread.first_message_id == message.pk:
        # In order to prevent an IntegrityError with
        # `UserThread.objects.bulk_create()` grab a list of all users with
        # existing subscriptions should they exist. Django is smart enough to
        # add this as a subquery for our `Subscription` query below instead of
        # doing 2 queries. Most of the time this will return only the sender
        # (who should already have a UserThread for this thread)
        existing_userthread_userids = UserThread.objects.with_deleted().filter(
            thread=thread).values_list('user_id', flat=True)

        # Get all users who are subscribed to a group.
        # We find group members via `Subscription` instead of `Group` as
        # we need information from `Subscription` and there is no ORM way of
        # joining the Many-to-Many between `User` and `Group` to `Subscription`
        group_subscriptions = Subscription.objects.filter(
            group=thread.group).exclude(
                user_id__in=existing_userthread_userids)

        # Iterate through each subscription to create a new userthread
        userthreads = []
        for subscription in group_subscriptions:

            # Determine if there should be a new email subscription for this
            # thread
            if subscription.period == 'none':
                subscribe_to_thread = False
            else:
                subscribe_to_thread = True

            # As we're going to use django's `bulk_create()` method, we'll need
            # a list of `UserThread` objects for each recipient.
            userthreads += [
                UserThread(
                    thread=thread,
                    user_id=subscription.user_id,
                    subscribed_email=subscribe_to_thread
                )
            ]

        if userthreads:
            # Let django batch-insert all the new userthreads
            UserThread.objects.bulk_create(userthreads)
    else:
        UserThread.objects.filter(
            thread=thread, read=True).exclude(user=sender).update(read=False)
        UserThread.objects.filter(
            thread=thread, status='archived'
        ).exclude(user=sender).update(status='active')

    if thread.thread_type == 'group':
        create_group_notifications.delay(message_id)

    # At this point lets mark the message as "sent"
    message.sent = True
    message.save(shorten=shorten)


@shared_task(name='send-system-message')
def send_system_message(recipient, subject, message_content):
    """Send a direct message to a user coming from the system user"""
    from open_connect.connectmessages.models import Thread, Message
    from open_connect.notifications.models import Notification
    from open_connect.accounts.models import User

    # Handle calls where we're passed the user_id instead of a User object.
    if not isinstance(recipient, User):
        recipient = User.objects.get(pk=recipient)

    sysuser = User.objects.get(email=settings.SYSTEM_USER_EMAIL)
    thread = Thread.objects.create(
        subject=subject[:100],
        thread_type='direct',
        closed=True
    )
    message = Message(
        thread=thread,
        sender=sysuser,
        text=message_content
    )
    message.save(shorten=False)
    thread.add_user_to_thread(recipient)

    # Use BeautifulSoup to remove any HTML from the message to make the
    # plaintext email version of the message
    notification, created = Notification.objects.get_or_create(
        recipient_id=recipient.pk,
        message=message
    )

    if created and recipient.group_notification_period == 'immediate':
        send_immediate_notification.delay(notification.pk)
