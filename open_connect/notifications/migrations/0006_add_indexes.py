# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_remove_queued_datetimes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='consumed',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='period',
            field=models.CharField(default=b'immediate', max_length=30, db_index=True, choices=[(b'none', b"Don't send email notifications"), (b'daily', b'Send a daily digest'), (b'immediate', b'Send me an email for every new message')]),
        ),
    ]
