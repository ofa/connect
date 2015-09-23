# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
        ('media', '0001_initial'),
        ('groups', '0002_add_default_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='image',
            field=models.ForeignKey(blank=True, to='media.Image', null=True),
        ),
        migrations.AddField(
            model_name='group',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='group',
            name='category',
            field=models.ForeignKey(default=1, verbose_name='Category', to='groups.Category'),
        ),
    ]
