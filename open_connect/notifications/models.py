"""Models for the notifications application."""

from django.conf import settings
from django.db import models

from open_connect.connect_core.utils.models import TimestampModel


NOTIFICATION_PERIODS = (
    ('none', 'Don\'t send email notifications'),
    ('daily', 'Send a daily digest'),
    ('immediate', 'Send me an email for every new message'),
)


class Subscription(TimestampModel):
    """Model for tracking a user's subscription preferences to a group."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='subscriptions')
    period = models.CharField(
        max_length=30, choices=NOTIFICATION_PERIODS, default='immediate',
        db_index=True)
    group = models.ForeignKey('groups.Group')

    class Meta(object):
        """Meta options for Subcription model."""
        unique_together = ['user', 'group']

    def save(self, *args, **kwargs):
        """Save method for Subscription"""
        # Importing from models to address circular import
        from open_connect.connectmessages.models import UserThread
        # Check to see if there is already a primary key (aka, this is an edit)
        if self.pk:
            # Get the original version of this record
            orig = Subscription.objects.get(pk=self.pk)
            # Check to see if the version has changed to none
            if self.period == 'none' and orig.period != 'none':
                # If the original record was not none (aka the period has
                # changed to 'none' from something else) update all UserThreads
                UserThread.objects.filter(
                    thread__group_id=self.group_id,
                    user_id=self.user_id,
                    subscribed_email=True
                ).update(subscribed_email=False)
            elif orig.period == 'none':
                UserThread.objects.filter(
                    thread__group_id=self.group_id,
                    user_id=self.user_id,
                    subscribed_email=False
                ).update(subscribed_email=True)

        return super(Subscription, self).save(*args, **kwargs)

    def __unicode__(self):
        """Unicode representation of the model."""
        return u'Subscription to {group} for {user}.'.format(
            group=self.group, user=self.user)


class Notification(TimestampModel):
    """Information about an individual notification."""
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL)
    consumed = models.BooleanField(default=False, db_index=True)
    subscription = models.ForeignKey(Subscription, blank=True, null=True)
    message = models.ForeignKey('connectmessages.Message')

    class Meta(object):
        """Meta options for Notification model."""
        # There should only ever be 1 notification per message
        unique_together = ['recipient', 'message']
