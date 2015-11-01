"""Group models."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup, Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.db.models.signals import m2m_changed
from django.utils.safestring import mark_safe
from taggit.managers import TaggableManager
from taggit.models import Tag
import autocomplete_light

from open_connect.media.models import Image, ShortenedURL
from open_connect.connectmessages.models import Thread, Message
from open_connect.connect_core.utils.location import get_coordinates, STATES
from open_connect.connect_core.utils.models import TimestampModel
from open_connect.groups.tasks import remove_user_from_group


autocomplete_light.register(Tag)

GROUP_STATUSES = (
    ('active', 'Active'),
    ('deleted', 'Deleted')
)


class Category(TimestampModel):
    """Group Category"""
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=127)
    color = models.CharField(
        verbose_name='Category Color', max_length=7, default='#000000')

    class Meta(object):
        """Meta options for Category model"""
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


    def __unicode__(self):
        """Unicode Representation of Category"""
        return self.name



class GroupManager(models.Manager):
    """Manager for Group model."""
    def get_queryset(self):
        """
        Ensures that all queries fror groups also queries the auth group
        model
        """
        return super(GroupManager, self).get_queryset().select_related(
            'group', 'category').exclude(status='deleted')

    def with_deleted(self):
        """Includes deleted groups."""
        return super(GroupManager, self).get_queryset().select_related(
            'group', 'category')

    # pylint: disable=no-self-use
    def create(self, **kwargs):
        """Create a new group."""
        name = kwargs.pop('name', None)
        if 'group' not in kwargs and name:
            kwargs['group'] = AuthGroup.objects.create(name=name)
        return super(GroupManager, self).create(**kwargs)

    def published(self, **kwargs):
        """Get published groups."""
        return self.get_queryset().filter(published=True, **kwargs)

    def search(self, search=None, location=None):
        """Groups search"""
        groups = Group.objects.published().select_related('image', 'group')
        if search:
            groups = groups.filter(
                Q(group__name__icontains=search)
                | Q(category__name__icontains=search)
                | Q(description__icontains=search)
                | Q(tags__slug__icontains=search)
            ).distinct()

        if location:
            groups = self.location_search(location, queryset=groups)

        return groups

    def location_search(self, location, queryset=None):
        """Groups search by location."""
        coords = get_coordinates(location)

        # If no coordinates are provided, return an empty queryset
        if not coords:
            return Group.objects.none()

        if queryset is None:
            queryset = Group.objects.published()

        # Pass the job of finding distance to the database using this query
        sql = (
            'SELECT '
            '(degrees(acos( '
            'sin(radians(latitude)) '
            '* sin(radians(%s)) '
            '+ cos(radians(latitude)) '
            '* cos(radians(%s)) '
            '* cos(radians(longitude - %s) ) '
            ') ) * 69.09)'
        )

        result = queryset.extra(
            select={'distance': sql},
            select_params=(coords[0], coords[0], coords[1]),

            # We use the same SQL again to do filtering by distance and
            # radius. We cannot use the param in the `SELECT` because
            # of a postgres limitation
            where=['(' + sql + ') <= "groups_group"."radius"'],
            params=(coords[0], coords[0], coords[1]),

            order_by=['-featured', 'distance', 'group__name']
        ).distinct()

        return result


class Group(TimestampModel):
    """Group model."""
    group = models.OneToOneField(AuthGroup)
    private = models.BooleanField(
        default=False,
        help_text='Membership to private groups is moderated.'
    )
    published = models.BooleanField(
        default=True,
        verbose_name=u'Publish this group',
        help_text='Published groups can be seen by all users.'
                  ' Unpublished groups can only be seen if'
                  ' you have the link.'
    )
    moderated = models.BooleanField(
        default=False,
        verbose_name=u'Moderate this group',
        help_text='Posts by users must be moderated by an admin.'
    )
    featured = models.BooleanField(
        default=False,
        verbose_name=u'This is an official group',
        help_text='Official groups are managed by staff and '
                  'appear first in search results.',
        db_index=True
    )
    member_list_published = models.BooleanField(
        default=True,
        help_text='Group member list is public'
    )
    category = models.ForeignKey(
        'groups.Category', verbose_name=u'Category', default=1)
    display_location = models.CharField(blank=True, max_length=100)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    radius = models.IntegerField(blank=True, null=True)
    is_national = models.BooleanField(default=True, db_index=True)
    # owners get permissions using a receiver below: group_owners_changed
    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='owned_groups_set')
    whitelist_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='whitelist_set'
    )
    description = models.TextField(blank=True)
    tags = TaggableManager(blank=True)
    image = models.ForeignKey(Image, blank=True, null=True)
    state = models.CharField(
        max_length=3,
        choices=[(s, s) for s in STATES],
        blank=True,
        db_index=True
    )
    tos_accepted_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    status = models.CharField(
        choices=GROUP_STATUSES,
        default='active',
        db_index=True,
        max_length=50
    )

    objects = GroupManager()

    class Meta(object):
        # pylint: disable=no-init,too-few-public-methods
        """Group meta options."""
        ordering = ['-featured', '-is_national', 'group__name']
        permissions = (
            ('can_edit_any_group', 'Can edit any group.'),
        )

    def __unicode__(self):
        """Convert group to a unicode string."""
        return u'%s' % self.group.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """Override save to auto-set is_national."""
        if not all([self.longitude, self.latitude, self.radius]):
            self.is_national = True
        else:
            self.is_national = False

        return super(Group, self).save(
            force_insert, force_update, using, update_fields)

    def delete(self, using=None):
        """Don't actually delete."""
        self.status = 'deleted'
        self.save()
        for user in self.group.user_set.all().iterator():
            remove_user_from_group.delay(user=user, group=self)

    def get_absolute_url(self):
        """Get the full local URL of an object"""
        return reverse('group_details', args=(self.pk,))

    @property
    def full_url(self):
        """The URL (including the origin) of the group detail page"""
        return settings.ORIGIN + self.get_absolute_url()

    def clean(self):
        """Custom group validation."""
        required_together = [
            self.latitude, self.longitude, self.radius]
        if any(required_together) and not all(required_together):
            raise ValidationError(
                "If a location is specified, name, latitude,"
                " longitude, and radius are required."
            )

    def get_members(self):
        """Return a queryset of all users in the group."""
        return self.group.user_set.all()

    def get_members_avatar_prioritized(self):
        """Return a queryset of group members prioritizing those with avatars"""
        # Selecting null as an extra column and sorting on that column
        # to preserve sorting when switching between MySQL and PostgreSQL.
        return self.get_members().extra(
            select={'image_null': 'image_id is null'}
        ).select_related('image').order_by('image_null')

    def public_threads_by_user(self, user):
        """All approved threads sent to group that the user is allowed to see"""
        return Thread.public.by_user(user).filter(group=self)

    def public_threads(self):
        """All the threads sent to this group."""
        return Thread.public.by_group(group=self)

    @property
    def unmoderated_messages(self):
        """
        Return all unmoderated messages
        """
        return Message.objects.filter(
            thread__group=self, status='pending')

    @property
    def total_unmoderated_messages(self):
        """
        Returns the total number of unmoderated messages
        """
        return self.unmoderated_messages.count()

    def images(self, user):
        """Returns popular images related to this group."""
        # We need to defer the exif field with distinct or postgres punches
        # you in the face. http://bit.ly/1k7HBs8
        return Image.popular.with_user(
            user=user
        ).filter(
            message__thread__group=self
        )

    def links(self):
        """Returns popular links related to this group."""
        return ShortenedURL.popular.filter(
            message__thread__group=self,
            message__status='approved')


def group_owners_changed(**kwargs):
    """
    Handle changes in group ownership.
    This could be broken out into 2 signal receivers, but that would involve
    2 duplicate queries to the User table to get a list of changed owners
    """

    # If this is a change in owners, grab the list of owners
    if kwargs['action'] in ['post_add', 'post_remove']:
        users = get_user_model().objects.filter(pk__in=kwargs['pk_set'])

        # Clear the user's 'owned_groups' cache
        for user in users:
            cache.delete(user.cache_key + 'owned_groups')

    # Make sure group owners can direct message all other users
    if kwargs['action'] == 'post_add':
        direct_message_permission = Permission.objects.get(
            codename='can_initiate_direct_messages',
            content_type__app_label='accounts')
        for user in users:
            user.user_permissions.add(direct_message_permission)


m2m_changed.connect(group_owners_changed, Group.owners.through)


class GroupRequestManager(models.Manager):
    """Manager for GroupRequest."""
    def unapproved(self):
        """Get unapproved requests."""
        return super(
            GroupRequestManager, self
        ).get_queryset().filter(moderated_by__isnull=True)


class GroupRequest(TimestampModel):
    """GroupRequest model."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    group = models.ForeignKey(Group)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        related_name='approved_by'
    )
    moderated_at = models.DateTimeField(blank=True, null=True)
    approved = models.NullBooleanField(blank=True)

    objects = GroupRequestManager()

    def __unicode__(self):
        """Convert GroupRequest to a unicode string."""
        return mark_safe(
            u'<a href="{url}">{name} ({email} / {state}, {zip_code})'
            u' requested to join {group}.</a>'.format(
                url=self.user.get_absolute_url(),
                email=self.user.email,
                state=self.user.state,
                zip_code=self.user.zip_code,
                name=self.user.get_real_name(),
                group=self.group
            )
        )
