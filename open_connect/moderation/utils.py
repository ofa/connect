"""Utilitis for the moderation app"""
from open_connect.connectmessages.models import Message, MESSAGE_STATUSES
from open_connect.moderation.models import MessageModerationAction
from open_connect.connectmessages.tasks import send_message

POSSIBLE_ACTIONS = [statuspair[0] for statuspair in MESSAGE_STATUSES]


def moderate_messages(actions, moderator):
    """Utility that processes moderation actions done by moderators"""
    total_changes = 0

    for action, message_ids in actions.iteritems():
        messages = Message.objects.filter(pk__in=message_ids)

        # If the user is not a superuser, we need to confirm that those messages
        # can be moderated by that staff member
        if not moderator.has_perm('accounts.can_moderate_all_messages'):
            messages = messages.filter(
                thread__group__in=moderator.groups_moderating)
        total_changes += messages.update(status=action)

        # Process each item
        for message in messages:
            moderation_action = MessageModerationAction.objects.create(
                message_id=message.pk,
                moderator=moderator,
                newstatus=action
            )
            message.flags.filter(
                moderation_action__isnull=True
            ).update(moderation_action=moderation_action)
            thread = message.thread
            thread.total_messages = thread.message_set.filter(
                status__in=['approved', 'flagged']).count()
            thread.save()
            if action == 'approved':
                send_message.delay(message.pk)

    return total_changes
