"""Celery tasks for connectmessages app."""
# pylint: disable=not-callable
from celery import shared_task
from django.conf import settings
from django.db import connection

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

        # We need to generate the UserThread objects for each group member. In
        # order to prevent a bunch of unnecessary talk between python and the
        # database which results in an INSERT containing almost no data python
        # was involved in generating, we can do this directly in the database.
        # This should also significantly speed up this task when sending new
        # threads to large groups.
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO connectmessages_userthread (
                    created_at,
                    modified_at,
                    thread_id,
                    user_id,
                    subscribed_email,
                    read,
                    status)

                SELECT
                    now(),              -- created_at (timestamp w/timezone)
                    now(),              -- modified_at (timestamp w/timezone)
                    %s,                 -- thread_id (integer)
                    s.user_id,          -- user_id (integer)
                    -- We base if someone is subscribed to a thread via email
                    -- through the notification period. Since this is a bool
                    -- in UserThread and a string in Subscription we need to
                    -- do a comparison operation here
                    s.period != 'none', -- subscribed_email (boolean)
                    False,              -- read (boolean)
                    'active'            -- status (varchar)

                -- We grab from notifications_subscription instead of from
                -- accounts_user_groups because we need information from the
                -- notifications_subscription table and the same data exists
                -- in both tables
                FROM notifications_subscription s

                WHERE
                    s.group_id = %s
                    AND
                    -- In order to prevent an IntegrityError, grab all users
                    -- with existing UserThread object and exclude them from
                    -- this insert. The only users who should have a UserThread
                    -- is the author and anyone who joined to the group between
                    -- the time the author posted the thread and the time this
                    -- task runs (in other words, not many users)
                    s.user_id NOT IN 
                        (SELECT user_id 
                        FROM connectmessages_userthread
                        WHERE thread_id = %s)
                """, [
                    thread.pk,
                    thread.group.pk,
                    thread.pk])

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
