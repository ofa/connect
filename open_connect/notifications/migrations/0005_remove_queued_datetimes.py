# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_set_consumed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notification',
            name='consumed_at',
        ),
        migrations.RemoveField(
            model_name='notification',
            name='queued_at',
        ),
        migrations.RemoveField(
            model_name='notification',
            name='triggered_at',
        ),
    ]
