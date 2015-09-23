# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import open_connect.connect_core.utils.models
import django_extensions.db.fields
import django.utils.timezone
from django.conf import settings
from pytz import common_timezones
from open_connect.connect_core.utils.location import STATES
import open_connect.accounts.models


TIMEZONE_CHOICES = [(tz, tz) for tz in common_timezones if tz.startswith('US/')]

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.TextField(max_length=200, unique=True, verbose_name='username')),
                ('email', models.EmailField(help_text=b'The email account notifications are sent to. This will not change the email address you use to login.', unique=True, max_length=254, verbose_name='Notification Email')),
                ('is_staff', models.BooleanField(default=False, verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=255, blank=True)),
                ('last_name', models.CharField(max_length=255, blank=True)),
                ('biography', models.TextField(blank=True)),
                ('timezone', models.CharField(default=b'US/Central', max_length=255, choices=TIMEZONE_CHOICES)),
                ('uuid', django_extensions.db.fields.UUIDField(max_length=36, editable=False, blank=True)),
                ('unsubscribed', models.BooleanField(default=False)),
                ('is_banned', models.BooleanField(default=False)),
                ('group_notification_period', models.CharField(default=b'immediate', max_length=50, verbose_name='Default Notification Setting', choices=[(b'none', b"Don't send email notifications"), (b'daily', b'Send a daily digest'), (b'immediate', b'Send me an email for every new message')])),
                ('direct_notification_period', models.CharField(default=b'immediate', max_length=50, choices=[(b'none', b"Don't send email notifications"), (b'daily', b'Send a daily digest'), (b'immediate', b'Send me an email for every new message')])),
                ('moderator_notification_period', models.IntegerField(default=1, help_text=b'Minimum time between notifications of new messages to moderate', verbose_name='Moderation Notification Time Period', choices=[(1, b'Hourly'), (4, b'Every 4 Hours'), (12, b'Every 12 Hours'), (24, b'Once Per Day'), (0, b'No New Moderation Notifications')])),
                ('phone', models.CharField(max_length=30, blank=True)),
                ('zip_code', models.CharField(max_length=10, blank=True)),
                ('state', models.CharField(blank=True, max_length=2, choices=[(state, state) for state in STATES])),
                ('facebook_url', models.URLField(blank=True)),
                ('twitter_handle', models.CharField(blank=True, max_length=20, validators=[open_connect.accounts.models.validate_twitter_handle])),
                ('website_url', models.URLField(blank=True)),
                ('invite_verified', models.BooleanField(default=True)),
                ('show_groups_on_profile', models.BooleanField(default=True, help_text='Can we display the groups you belong to on your public profile?')),
                ('tos_accepted_at', models.DateTimeField(null=True, blank=True)),
                ('ucoc_accepted_at', models.DateTimeField(null=True, blank=True)),
                ('has_viewed_tutorial', models.BooleanField(default=False)),
                ('receive_group_join_notifications', models.BooleanField(default=True, help_text='Would you like to receive notifications when new users join your groups?')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'permissions': (('can_view_banned', 'Can view banned users.'), ('can_ban', 'Can ban users.'), ('can_unban', 'Can unban users.'), ('can_view_user_report', 'Can view user report.'), ('can_view_group_report', 'Can view group report.'), ('can_impersonate', 'Can impersonate other users.'), ('can_moderate_all_messages', 'Can moderate all messages.'), ('can_initiate_direct_messages', 'Can initiate direct messages.'), ('can_modify_permissions', 'Can modify user permissions.'))
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='Invite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('email', models.EmailField(unique=True, max_length=254)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_superuser', models.BooleanField(default=False)),
                ('consumed_at', models.DateTimeField(null=True, blank=True)),
                ('notified', models.DateTimeField(null=True, editable=False)),
                ('code', models.CharField(default=open_connect.accounts.models.generate_unique_invite_code, max_length=32)),
                ('consumed_by', models.ForeignKey(related_name='consumed_invite', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'get_latest_by': 'created_at',
                'permissions': (('email_invites', 'Email Invites To Users'),),
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('ip_address', models.GenericIPAddressField(null=True, blank=True)),
                ('user_agent', models.TextField(blank=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
    ]
