"""Tasks for mailer app"""
# pylint: disable=not-callable
from datetime import timedelta

from django.utils.timezone import now
from celery import shared_task

from open_connect.mailer.models import EmailOpen


@shared_task()
def wipe_old_email_opens():
    """Clear old email opens"""
    # We don't need/care about email opens older than 2 weeks
    EmailOpen.objects.exclude(
        opened_at__gte=now()-timedelta(weeks=2)).delete()
