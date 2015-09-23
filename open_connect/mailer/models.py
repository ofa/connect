"""Models for the mailer app"""
# pylint: disable=too-many-instance-attributes
import hashlib
import logging

from django.core.cache import cache
from django.conf import settings
from django.db import models

from open_connect.accounts.models import User
from open_connect.connect_core.utils.models import TimestampModel

UNSUBSCRIBE_SOURCES = (
    ('bounce', 'Bounce Report'),
    ('user', 'End User'),
)


LOGGER = logging.getLogger('mailer.models')


def _cache_name(address):
    """Generates the key name of an object's cache entry"""
    addr_hash = hashlib.md5(address).hexdigest()
    return "unsub-{hash}".format(hash=addr_hash)


class EmailOpen(models.Model):
    """Email open model"""
    opened_at = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(db_index=True)
    key = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    notification = models.IntegerField(null=True, blank=True)
    device_family = models.CharField(
        max_length=255, null=True, blank=True, db_index=True)
    browser = models.CharField(
        max_length=255, null=True, blank=True, db_index=True)
    operating_system = models.CharField(
        max_length=50, null=True, blank=True, db_index=True)
    referrer = models.URLField(max_length=255, null=True, blank=True)
    referrer_netloc = models.URLField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        """Save the instance."""
        # There are some LONG user agents out there, but the useful stuff is
        # generally at the beginning. Let's just throw away the garbage at the
        # end that won't fit. (Usually a list of patch IDs on Windows systems)
        self.user_agent = self.user_agent[:255]

        # Handle long referrer URLs.
        if self.referrer:
            self.referrer = self.referrer[:255]

        if self.referrer_netloc:
            self.referrer_netloc = self.referrer_netloc[:255]

        return super(EmailOpen, self).save(*args, **kwargs)


class UnsubscribeManager(models.Manager):
    """Manager for the Unsubscribe model"""
    def address_exists(self, address):
        """Determine if an address exists in the database"""
        # Try to grab an existing record from the cache
        cache_copy = cache.get(_cache_name(address))
        if cache_copy:
            # If a cache copy exists and is not False, return True
            return True
        elif cache_copy == False:
            # If it's a False result (i.e. we've already checked that address
            # and no record exists) return False
            return False
        else:
            # If the cache is completely empty (i.e. returns None) check the
            # database
            result = self.get_queryset().filter(address=address).first()
            if result:
                cache.set(_cache_name(result.address), result)
                return True
            else:
                cache.set(_cache_name(address), False)
                return False


class Unsubscribe(TimestampModel):
    """Unsubscribe action model"""
    address = models.EmailField(db_index=True)
    source = models.CharField(choices=UNSUBSCRIBE_SOURCES, max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)

    objects = UnsubscribeManager()

    class Meta(object):
        """Meta class for Unsubscribe model"""
        verbose_name = 'Unsubscribe'
        verbose_name_plural = 'Unsubscribes'

    def __unicode__(self):
        """Unicode method for Unsubscribe model"""
        return u"Unsubscribe %s" % self.address

    def save(self, *args, **kwargs):
        """Save method for Unsubscribe model"""
        # If there isn't a user attached to this unsubscribe, try to attach one
        if not self.user:
            self.user = self.match_user()

        result = super(Unsubscribe, self).save(*args, **kwargs)

        cache.set(_cache_name(self.address), self)

        LOGGER.info('Unsubscribe Type: %s Email: %s',
                    self.source, self.address)

        return result

    def delete(self, *args, **kwargs):
        """Method to delete the Unsubscribe object"""
        cache.delete(_cache_name(self.address))
        return super(Unsubscribe, self).delete(*args, **kwargs)

    def match_user(self):
        """Method that returns a User associated with an email if one exists"""
        try:
            user = User.objects.get(email=self.address)
        except User.DoesNotExist:
            user = None

        return user
