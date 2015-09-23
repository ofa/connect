# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import open_connect.connect_core.utils.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Flag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('flagged_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='ModerationAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('comment', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Moderation Action',
                'verbose_name_plural': 'Moderation Actions',
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='MessageModerationAction',
            fields=[
                ('moderationaction_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='moderation.ModerationAction')),
                ('newstatus', models.CharField(default=b'approved', max_length=50, choices=[(b'approved', b'Approved'), (b'flagged', b'Flagged'), (b'spam', b'Spam'), (b'pending', b'Pending Moderator Approval'), (b'vetoed', b'Vetoed'), (b'deleted', b'Deleted')])),
            ],
            options={
                'verbose_name': 'Message Moderation Action',
                'verbose_name_plural': 'Message Moderation Actions',
            },
            bases=('moderation.moderationaction',),
        ),
        migrations.AddField(
            model_name='moderationaction',
            name='moderator',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='flag',
            name='moderation_action',
            field=models.ForeignKey(blank=True, to='moderation.ModerationAction', null=True),
        ),
    ]
