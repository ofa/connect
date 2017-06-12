"""Accounts tasks"""
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.timezone import now

from open_connect.mailer.utils import send_email


@shared_task()
def render_and_send_invite_email(invite_id):
    """Renders and sends an invite email."""
    from open_connect.accounts.models import Invite
    invite = Invite.objects.get(pk=invite_id)

    if invite.notified:
        return

    context = {
        'invite': invite,
        'email': invite.email,
        'origin': settings.ORIGIN
    }
    html = render_to_string(
        'account/email/new_user_invite.html', context)
    text = render_to_string(
        'account/email/new_user_invite.txt', context)

    send_email(
        email=invite.email,
        from_email=settings.DEFAULT_FROM_EMAIL,
        subject=u"You're invited to Connect",
        text=text,
        html=html
    )

    invite.notified = now()
    invite.save()
