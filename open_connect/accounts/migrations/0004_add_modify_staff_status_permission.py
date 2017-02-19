# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_create_system_user'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users', 'permissions': (('can_view_banned', 'Can view banned users.'), ('can_ban', 'Can ban users.'), ('can_unban', 'Can unban users.'), ('can_view_user_report', 'Can view user report.'), ('can_view_group_report', 'Can view group report.'), ('can_impersonate', 'Can impersonate other users.'), ('can_moderate_all_messages', 'Can moderate all messages.'), ('can_initiate_direct_messages', 'Can initiate direct messages.'), ('can_modify_permissions', 'Can modify user permissions.'), ('can_modify_staff_status', "Can modify a user's staff status"))},
        ),
    ]
