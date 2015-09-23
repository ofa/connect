# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import models, migrations
from django.utils.timezone import now


def create_system_user(apps, schema_editor):
    """Create a new system user if one does not exist"""
    User = apps.get_model('accounts', 'User')

    system_user_email = getattr(
        settings, 'CONNECT_SYSTEM_USER_EMAIL', 'no-reply@localhost')

    # As apps.get_model() does not expose `set_unusable_password` we must make
    # our own unusable password. This can be done by sending `None` to
    # `make_password`
    unuseable_password = make_password(None)

    user, created = User.objects.get_or_create(
        email=system_user_email,
        defaults={
            'username': system_user_email,
            'is_active': True,
            'is_superuser': True,
            'last_login': now(),
            'date_joined': now(),
            'password': unuseable_password
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_foreign_keys'),
    ]

    operations = [
        migrations.RunPython(create_system_user),
    ]
