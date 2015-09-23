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
            name='EmailOpen',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('opened_at', models.DateTimeField(auto_now_add=True)),
                ('email', models.EmailField(max_length=254, db_index=True)),
                ('key', models.CharField(max_length=50, db_index=True)),
                ('timestamp', models.DateTimeField()),
                ('ip_address', models.GenericIPAddressField(null=True, blank=True)),
                ('user_agent', models.CharField(max_length=255, null=True, blank=True)),
                ('notification', models.IntegerField(null=True, blank=True)),
                ('device_family', models.CharField(db_index=True, max_length=255, null=True, blank=True)),
                ('browser', models.CharField(db_index=True, max_length=255, null=True, blank=True)),
                ('operating_system', models.CharField(db_index=True, max_length=50, null=True, blank=True)),
                ('referrer', models.URLField(max_length=255, null=True, blank=True)),
                ('referrer_netloc', models.URLField(max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Unsubscribe',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('address', models.EmailField(max_length=254, db_index=True)),
                ('source', models.CharField(max_length=50, choices=[(b'bounce', b'Bounce Report'), (b'user', b'End User')])),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name': 'Unsubscribe',
                'verbose_name_plural': 'Unsubscribes',
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
    ]
