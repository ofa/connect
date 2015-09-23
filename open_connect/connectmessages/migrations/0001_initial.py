# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import open_connect.connect_core.utils.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('media', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImageAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('image', models.ForeignKey(to='media.Image')),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('ip_address', models.GenericIPAddressField(null=True, blank=True)),
                ('user_agent', models.TextField(null=True, blank=True)),
                ('text', models.TextField()),
                ('clean_text', models.TextField(blank=True)),
                ('status', models.CharField(default=b'pending', max_length=50, db_index=True, choices=[(b'approved', b'Approved'), (b'flagged', b'Flagged'), (b'spam', b'Spam'), (b'pending', b'Pending Moderator Approval'), (b'vetoed', b'Vetoed'), (b'deleted', b'Deleted')])),
                ('sent', models.BooleanField(default=False)),
                ('wiped', models.BooleanField(default=False)),
                ('images', models.ManyToManyField(to='media.Image', blank=True)),
                ('links', models.ManyToManyField(to='media.ShortenedURL', blank=True)),
                ('sender', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='Thread',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('subject', models.CharField(max_length=255)),
                ('thread_type', models.CharField(default=b'group', max_length=50, choices=[(b'direct', b'Direct Message'), (b'group', b'Group Message')])),
                ('total_messages', models.IntegerField(default=1)),
                ('visible', models.BooleanField(default=True, db_index=True, verbose_name='Visible to users')),
                ('closed', models.BooleanField(default=False, verbose_name='Closed to new comments')),
                ('status', models.CharField(default=b'active', max_length=50, db_index=True, choices=[(b'active', b'Active'), (b'deleted', b'Deleted')])),
                ('first_message', models.ForeignKey(related_name='message_threadstarter', blank=True, to='connectmessages.Message', null=True)),
                ('group', models.ForeignKey(to='groups.Group', null=True)),
                ('latest_message', models.ForeignKey(related_name='message_latestinthread', blank=True, to='connectmessages.Message', null=True)),
            ],
            options={
                'ordering': ['-latest_message__created_at'],
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='UserThread',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('read', models.BooleanField(default=False, db_index=True, verbose_name='Thread Read')),
                ('last_read_at', models.DateTimeField(null=True, blank=True)),
                ('subscribed_email', models.BooleanField(default=True, help_text=b'Subscribed to receive new message alerts via email', verbose_name='Subscribed for Email')),
                ('status', models.CharField(default=b'active', max_length=50, db_index=True, choices=[(b'active', b'Active'), (b'archived', b'Archived'), (b'deleted', b'Deleted')])),
                ('thread', models.ForeignKey(to='connectmessages.Thread')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.AddField(
            model_name='thread',
            name='recipients',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, through='connectmessages.UserThread', blank=True),
        ),
        migrations.AddField(
            model_name='message',
            name='thread',
            field=models.ForeignKey(to='connectmessages.Thread', blank=True),
        ),
        migrations.AddField(
            model_name='imageattachment',
            name='message',
            field=models.ForeignKey(to='connectmessages.Message'),
        ),
        migrations.AlterUniqueTogether(
            name='userthread',
            unique_together=set([('thread', 'user')]),
        ),
        migrations.AlterIndexTogether(
            name='userthread',
            index_together=set([('thread', 'subscribed_email'), ('user', 'read')]),
        ),
    ]
