# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
import open_connect.connect_core.utils.models
import open_connect.connect_core.utils.storages
from django.conf import settings
import django.core.validators
import django_extensions.db.fields
import open_connect.media.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(storage=open_connect.connect_core.utils.storages.AttachmentStorage(), width_field=b'image_width', height_field=b'image_height', upload_to=b'attachments/images/', max_length=250, blank=True)),
                ('display_image', models.ImageField(storage=open_connect.connect_core.utils.storages.HighValueStorage(), max_length=250, upload_to=b'attachments/images/', blank=True)),
                ('thumbnail', models.ImageField(storage=open_connect.connect_core.utils.storages.HighValueStorage(), max_length=250, upload_to=b'attachments/thumbnails/images/', blank=True)),
                ('exif', jsonfield.fields.JSONField(null=True, blank=True)),
                ('image_height', models.IntegerField(editable=False)),
                ('image_width', models.IntegerField(editable=False)),
                ('view_count', models.PositiveIntegerField(default=0)),
                ('promoted', models.BooleanField(default=False)),
                ('uuid', django_extensions.db.fields.UUIDField(db_index=True, max_length=36, editable=False, blank=True)),
                ('user', models.ForeignKey(related_name='images', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-promoted', '-created_at'],
                'get_latest_by': 'created_at',
                'permissions': (('can_promote_image', 'Can promote an image'), ('can_access_admin_gallery', 'Can access the admin gallery')),
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='ShortenedURL',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('url', models.TextField(validators=[django.core.validators.URLValidator(), open_connect.media.validators.validate_unique_url])),
                ('short_code', models.CharField(db_index=True, unique=True, max_length=20, blank=True)),
                ('click_count', models.PositiveIntegerField(default=0)),
                ('message_count', models.PositiveIntegerField(default=0)),
            ],
            options={
                'get_latest_by': 'created_at',
                'permissions': (('can_access_popular_urls', 'Can access the popular url list'),),
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
        migrations.CreateModel(
            name='ShortenedURLClick',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('shortened_url', models.ForeignKey(to='media.ShortenedURL')),
            ],
            options={
                'abstract': False,
            },
            bases=(open_connect.connect_core.utils.models.CacheMixinModel, models.Model),
        ),
    ]
