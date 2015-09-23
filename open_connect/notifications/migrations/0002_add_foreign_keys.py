# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('connectmessages', '0001_initial'),
        ('groups', '0001_initial'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='message',
            field=models.ForeignKey(default=1, to='connectmessages.Message'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='group',
            field=models.ForeignKey(default=1, to='groups.Group'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='subscription',
            unique_together=set([('user', 'group')]),
        ),
        migrations.AlterUniqueTogether(
            name='notification',
            unique_together=set([('recipient', 'message')]),
        ),
    ]
