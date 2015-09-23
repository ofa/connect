# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import open_connect.connect_core.utils.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('private', models.BooleanField(default=False, help_text=b'Membership to private groups is moderated.')),
                ('published', models.BooleanField(default=True, help_text=b'Published groups can be seen by all users. Unpublished groups can only be seen if you have the link.', verbose_name='Publish this group')),
                ('moderated', models.BooleanField(default=False, help_text=b'Posts by users must be moderated by an admin.', verbose_name='Moderate this group')),
                ('featured', models.BooleanField(default=False, help_text=b'Official groups are managed by staff and appear first in search results.', db_index=True, verbose_name='This is an official group')),
                ('member_list_published', models.BooleanField(default=True, help_text=b'Group member list is public')),
                ('display_location', models.CharField(max_length=100, blank=True)),
                ('latitude', models.FloatField(null=True, blank=True)),
                ('longitude', models.FloatField(null=True, blank=True)),
                ('radius', models.IntegerField(null=True, blank=True)),
                ('is_national', models.BooleanField(default=True, db_index=True)),
                ('description', models.TextField(blank=True)),
                ('state', models.CharField(blank=True, max_length=3, db_index=True, choices=[(b'AL', b'AL'), (b'AK', b'AK'), (b'AZ', b'AZ'), (b'AR', b'AR'), (b'CA', b'CA'), (b'CO', b'CO'), (b'CT', b'CT'), (b'DE', b'DE'), (b'DC', b'DC'), (b'FL', b'FL'), (b'GA', b'GA'), (b'HI', b'HI'), (b'ID', b'ID'), (b'IL', b'IL'), (b'IN', b'IN'), (b'IA', b'IA'), (b'KS', b'KS'), (b'KY', b'KY'), (b'LA', b'LA'), (b'ME', b'ME'), (b'MD', b'MD'), (b'MA', b'MA'), (b'MI', b'MI'), (b'MN', b'MN'), (b'MS', b'MS'), (b'MO', b'MO'), (b'MT', b'MT'), (b'NE', b'NE'), (b'NV', b'NV'), (b'NH', b'NH'), (b'NJ', b'NJ'), (b'NM', b'NM'), (b'NY', b'NY'), (b'NC', b'NC'), (b'ND', b'ND'), (b'OH', b'OH'), (b'OK', b'OK'), (b'OR', b'OR'), (b'PA', b'PA'), (b'RI', b'RI'), (b'SC', b'SC'), (b'SD', b'SD'), (b'TN', b'TN'), (b'TX', b'TX'), (b'UT', b'UT'), (b'VT', b'VT'), (b'VA', b'VA'), (b'WA', b'WA'), (b'WV', b'WV'), (b'WI', b'WI'), (b'WY', b'WY')])),
                ('tos_accepted_at', models.DateTimeField(null=True, blank=True)),
                ('status', models.CharField(default=b'active', max_length=50, db_index=True, choices=[(b'active', b'Active'), (b'deleted', b'Deleted')])),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
                ('group', models.OneToOneField(to='auth.Group')),
                ('owners', models.ManyToManyField(related_name='owned_groups_set', to=settings.AUTH_USER_MODEL, blank=True)),
                ('whitelist_users', models.ManyToManyField(related_name='whitelist_set', to=settings.AUTH_USER_MODEL, blank=True)),
            ],
            options={
                'ordering': ['-featured', '-is_national', 'group__name'],
                'permissions': (('can_edit_any_group', 'Can edit any group.'),)
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='GroupRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('moderated_at', models.DateTimeField(null=True, blank=True)),
                ('approved', models.NullBooleanField()),
                ('group', models.ForeignKey(to='groups.Group')),
                ('moderated_by', models.ForeignKey(related_name='approved_by', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('name', models.CharField(max_length=127)),
                ('color', models.CharField(default=b'#000000', max_length=7, verbose_name=b'Category Color')),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
    ]
