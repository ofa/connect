# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import taggit.managers


def create_default_category(apps, schema_editor):
    """Create a default category"""
    Category = apps.get_model("groups", "Category")
    Category.objects.get_or_create(
        slug='default', name='Default', color='#000000')


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
    ]

    operations = [
        # If forwards create a default category. If backwards don't do anything
        # and let the previous migration simply drop the table
        migrations.RunPython(create_default_category, lambda *args: None),
    ]
