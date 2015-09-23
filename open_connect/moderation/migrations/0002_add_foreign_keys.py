# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('connectmessages', '0001_initial'),
        ('moderation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='messagemoderationaction',
            name='message',
            field=models.ForeignKey(default=1, to='connectmessages.Message'),
            preserve_default=False,
        ),
    ]
