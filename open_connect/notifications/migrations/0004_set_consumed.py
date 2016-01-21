# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.utils.timezone import now


def create_consumed(apps, schema_editor):
    """Create a default category"""
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(
        consumed_at__isnull=True,
        queued_at__isnull=True).exclude(
        message__status='deleted').update(consumed=False)


def tear_down_consumed(apps, schema_editor):
    """
    Go backwards if the consumed field is to be removed

    By default mark every field as if it was consumed.
    """
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.update(consumed_at=now(), queued_at=now(), triggered_at=now())


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_add_consumed_bool'),
    ]

    operations = [
        # If forwards create a default consumption. If backwards don't do
        # anything and let the previous migration simply drop the column
        migrations.RunPython(create_consumed, tear_down_consumed),
    ]
