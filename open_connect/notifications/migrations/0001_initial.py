# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import open_connect.connect_core.utils.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('triggered_at', models.DateTimeField(null=True, blank=True)),
                ('queued_at', models.DateTimeField(null=True, blank=True)),
                ('consumed_at', models.DateTimeField(null=True, blank=True)),
                ('recipient', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('period', models.CharField(default=b'immediate', max_length=30, choices=[(b'none', b"Don't send email notifications"), (b'daily', b'Send a daily digest'), (b'immediate', b'Send me an email for every new message')])),
                ('user', models.ForeignKey(related_name='subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.AddField(
            model_name='notification',
            name='subscription',
            field=models.ForeignKey(blank=True, to='notifications.Subscription', null=True),
        ),
    ]
