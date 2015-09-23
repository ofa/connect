# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import open_connect.connect_core.utils.models
import taggit.managers
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('taggit', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('attachment', models.FileField(max_length=255, upload_to=b'resources')),
                ('content_type', models.CharField(default=b'text/plain', max_length=255)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200, editable=False)),
                ('uuid', django_extensions.db.fields.UUIDField(max_length=36, editable=False, blank=True)),
                ('status', models.CharField(default=b'active', max_length=20, choices=[(b'active', b'Active'), (b'deleted', b'Deleted')])),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('groups', models.ManyToManyField(to='groups.Group')),
                ('tags', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
            options={
                'permissions': (('can_add_resource_anywhere', 'Can create resources anywhere.'),),
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
    ]
