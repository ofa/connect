# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models



class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_add_foreign_keys'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='consumed',

            # The actual default is `False`, but if we set the default here
            # to `True` we can avoid a heavy full-table UPDATE() in the next
            # migration to reflect that most notifications have already been
            # consumed.
            field=models.BooleanField(default=True)
        ),

    ]
