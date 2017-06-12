"""Signal handlers for Account-related tasks"""
from django.dispatch import receiver
from allauth.account.signals import email_changed


@receiver(email_changed)
def change_user_email(sender, **kwargs):
    """Handle changes to user email addresses in django allauth

    Django Allauth lets users change their primary email address. This should
    also change the email address in their account and where their emails go
    to.
    """
    user = kwargs['user']
    user.email = kwargs['to_email_address'].email
    user.save(update_fields=['email'])
