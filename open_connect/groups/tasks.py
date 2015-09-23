"""Group tasks."""
# pylint: disable=not-callable
import logging

from celery import shared_task
from django.core.cache import cache
from django.db import connection
from django.template.loader import render_to_string

from open_connect.connectmessages.tasks import send_system_message
from open_connect.groups import group_member_added, group_member_removed


LOGGER = logging.getLogger('groups.tasks')


@shared_task(name='add-user-to-group')
def add_user_to_group(user_id, group_id, notification=None, period=None):
    """A task that will add a user_id to a group.

    Arguments:
    * user_id - User ID for a user
    * group - Group ID for a group

    Optional Kwargs:
    * notification - A tuple of a subject and a message that will be sent from
                     a system user to the user added to the group. The format
                     is ('Subject', 'Message')
    * period - A string indicating the subscription period desired. Defaults to
               the user's default notification period.

    Upon success this task fires the `open_connect.groups.group_member_added`
    signal providing the 'user' and 'group'
    """
    from open_connect.notifications.models import Subscription
    from open_connect.connectmessages.models import Thread, UserThread
    from open_connect.accounts.models import User
    from open_connect.groups.models import Group

    user = User.objects.get(pk=user_id)
    group = Group.objects.select_related('group').get(pk=group_id)

    if not period:
        period = user.group_notification_period

    # Add a Subscription
    subscription, created = Subscription.objects.get_or_create(
        user_id=user.pk, group=group, defaults={'period': period})

    # If the user already has a subscription, bail out
    if user.groups.filter(group=group).exists() or not created:
        return

    # Add to the django group
    user.groups.add(group.group)

    # Find out what threads this user already has. This way we don't
    # have to do a get_or_create for each thread on the off-chance a user
    # is a previous member of the group
    existing_userthreads = UserThread.objects.with_deleted().filter(
        user_id=user.pk, thread__group=group)
    # Update existing userthreads
    existing_userthreads.update(status='active')
    group_threads = Thread.objects.filter(
        group=group
    ).exclude(
        pk__in=existing_userthreads.values_list('thread', flat=True)
    )

    subscribed_to_email = subscription.period != 'none'
    new_userthreads = []
    for thread in group_threads:
        new_userthreads += [
            UserThread(
                user=user,
                thread=thread,
                subscribed_email=subscribed_to_email,
                read=True
            )]

    # Create all the new userthreads
    UserThread.objects.bulk_create(new_userthreads)

    # Clear the user's 'groups joined' cache
    cache.delete(user.cache_key + 'groups_joined')

    # If necessary, notify the user they've been added to the group
    if notification:
        send_system_message.delay(
            user.pk,
            notification[0],
            notification[1]
        )

    # Send a message to the group owners letting them know about the new member.
    subject = u'Your group {group} has a new member.'.format(
        group=group.group.name)
    message = (
        u'The user <a href="{user_link}">{user}</a>'
        u' has joined <a href="{group_link}">{group}</a>.'.format(
            user_link=user.full_url,
            user=user.get_full_name(),
            group_link=group.full_url,
            group=group.group.name
        )
    )
    for owner in group.owners.filter(
            receive_group_join_notifications=True).iterator():
        send_system_message.delay(
            recipient=owner.pk,
            subject=subject,
            message_content=message
        )

    # Send a signal notifying that a group member was added
    group_member_added.send(Group, user=user, group=group)


@shared_task(name='remove-user-from-group')
def remove_user_from_group(user, group):
    """A task that will remove a user to a group.

    Arguments:
    * user - Either a User object or a User ID (use id if calling as a task)
    * group - Either a Group object or Group ID (same as user)

    To reduce unnecessary queries, you can pass in a User/Group object or a
    User/Group id. Tasks generally should pass in the ID, while those calling
    this at runtime should pass in the object itself.

    Upon success this task fires the `open_connect.groups.group_member_removed`
    signal providing the 'user' and 'group'
    """
    from open_connect.notifications.models import Subscription
    from open_connect.connectmessages.models import UserThread
    from open_connect.accounts.models import User
    from open_connect.groups.models import Group

    if not isinstance(user, User):
        user = User.objects.get(pk=user)

    if not isinstance(group, Group):
        group = Group.objects.select_related('group').get(pk=group)

    LOGGER.debug(
        'Removing %s from %s', user.pk, group.pk)

    # Find out which threads the user is already a participant in
    query = ("SELECT thread_id from connectmessages_message"
             " WHERE sender_id = %s GROUP BY thread_id")
    cursor = connection.cursor()

    cursor.execute(query, [user.pk])

    participated_threads = [int(result[0]) for result in cursor.fetchall()]

    # Delete all userthreads a user is not participating in.
    UserThread.objects.filter(
        user=user,
        thread__group=group
    ).exclude(
        thread_id__in=participated_threads
    ).update(
        status='deleted'
    )

    # Remove the user from being an owner
    group.owners.remove(user)

    # Remove the user's subscription (as well as their notifications)
    subscription = Subscription.objects.get(user=user, group=group)
    subscription.delete()

    # Remove the user from the django group
    user.groups.remove(group.group)

    # Clear the user's 'groups joined' cache
    cache.delete(user.cache_key + 'groups_joined')

    # Send a signal notifying that a group member was removed
    group_member_removed.send(Group, user=user, group=group)


def import_group():
    """Avoid circular dependency import error but still make this mockable."""
    from open_connect.groups.models import Group
    return Group


@shared_task(name='process-group-image')
def process_group_images(group_id):
    """Run any tasks necessary to process a new/updated image attachment."""
    group_model = import_group()
    group = group_model.objects.get(pk=group_id)
    group.create_display_size()
    group.create_thumbnail()


@shared_task(name='notify-group-owners-of-request')
def notify_owners_of_group_request(request_id):
    """Emails group owners when there is a request to join a group."""
    from open_connect.groups.models import GroupRequest

    request = GroupRequest.objects.get(pk=request_id)
    context = {
        'user': request.user,
        'group': request.group
    }
    notification_html = render_to_string(
        'groups/notifications/group_request_owner_notification.html', context)

    for owner in request.group.owners.all():
        send_system_message.delay(
            owner.pk,
            'Request to join group {group}'.format(group=str(request.group)),
            notification_html
        )


@shared_task(name='invite-to-group')
def invite_users_to_group(emails, requester_id, group_id):
    """Process an invite action to a group"""
    from open_connect.groups.models import Group
    from open_connect.accounts.models import Invite
    from django.contrib.auth import get_user_model

    # pylint: disable=invalid-name
    User = get_user_model()
    requester = User.objects.get(pk=requester_id)
    group = Group.objects.select_related('group').get(pk=group_id)

    # Split emails if it is a string
    if isinstance(emails, (str, unicode)):
        emails = [email.strip() for email in emails.split(',')]
        LOGGER.debug('Processing %s emails: %s', len(emails), emails)

    # Grab a queryset of all users who are already members
    existing_users = User.objects.filter(email__in=emails)

    subject = u"You've been added to {group}".format(group=unicode(group))
    message = render_to_string(
        'groups/notifications/added_to_group_notification.html',
        {'group': group}
    )

    # For each existing user, add them to the group
    for existing_user in existing_users:
        LOGGER.debug(
            'Adding %s to %s', existing_user.email, group
        )
        existing_user.add_to_group(group.pk, notification=(subject, message))

    # Grab a list of all emails that are not associated with an existing user
    existing_emails = existing_users.values_list('email', flat=True)
    new_emails = set(emails).difference(set(existing_emails))

    # Invite new users and add group to invite.
    for email in new_emails:
        LOGGER.debug(
            'Inviting %s to %s', email, group)
        invite, _ = Invite.objects.get_or_create(
            email=email,
            defaults={'created_by': requester}
        )
        invite.groups.add(group)
        invite.send_invite(sender_id=requester.pk)
