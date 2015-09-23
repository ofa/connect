# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('moderation', '0001_initial'),
        ('connectmessages', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='flags',
            field=models.ManyToManyField(to='moderation.Flag', blank=True),
        ),
    ]
