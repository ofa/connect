# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0003_add_foreign_keys'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='group',
            options={'ordering': ['-featured', '-is_national', 'group__name'], 'permissions': (('can_edit_any_group', 'Can edit any group.'), ('can_edit_group_category', "Can change a group's category."), ('can_edit_group_featured', "Can change a group's featured status."))},
        ),
    ]
