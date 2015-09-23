"""Models for the moderation app"""

from django.conf import settings
from django.db import models

from open_connect.connect_core.utils.models import TimestampModel
from open_connect.connectmessages.models import Message, MESSAGE_STATUSES


class ModerationAction(TimestampModel):
    """List of all moderation actions"""
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL)
    comment = models.TextField(blank=True)

    class Meta(object):
        """Meta properties for ModerationAction model"""
        verbose_name = 'Moderation Action'
        verbose_name_plural = 'Moderation Actions'
        ordering = ['-created_at']

    def __unicode__(self):
        """Unicode representation of a ModerationAction"""
        return u"Moderation action by %s" % self.moderator


class MessageModerationAction(ModerationAction):
    """List of message moderation actions"""
    message = models.ForeignKey(Message)
    newstatus = models.CharField(
        default='approved', choices=MESSAGE_STATUSES, max_length=50)

    class Meta(object):
        """Meta properties for MessageModerationAction model"""
        verbose_name = 'Message Moderation Action'
        verbose_name_plural = 'Message Moderation Actions'

    def __unicode__(self):
        """Unicode representation of a MessageModerationAction"""
        return u"Moderation of %s by %s" % (self.message, self.moderator)


class Flag(TimestampModel):
    """Model for storing flags and associated moderation actions."""
    flagged_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    moderation_action = models.ForeignKey(
        ModerationAction, blank=True, null=True)
