"""Django Allauth Adapter"""
from allauth.account.adapter import DefaultAccountAdapter
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

from open_connect.mailer.backend import ConnectMailerBackend, DefaultBackend


class AccountAdapter(DefaultAccountAdapter):
    """Custom adapter for Django Allauth"""

    def render_mail(self, template_prefix, email, context):
        """Method to render and generate an email message

        Renders an email sent to `email` and returns a django EmailMessage

        Args:
            template_prefix: Email to be sent (the prefix on a template path.)
                             e.g. "account/email/email_confirmation"
            email: Email address of the recipient of the email
            context: Context to be passed into the django template engine
        """

        if settings.ACCOUNT_IGNORE_UNSUBSCRIBE:
            connection = DefaultBackend()
        else:
            connection = ConnectMailerBackend()

        context['email'] = email
        context['recipient'] = context['user']

        subject = render_to_string(
            '{0}_subject.txt'.format(template_prefix), context)
        # Remove unnecessary line breaks
        subject = " ".join(subject.splitlines()).strip()

        text_email = render_to_string(
            '{0}_message.txt'.format(template_prefix), context)
        html_email = render_to_string(
            '{0}_message.html'.format(template_prefix), context)

        message = EmailMultiAlternatives(
            subject=subject,
            body=text_email,
            from_email=self.get_from_email(),
            to=(email,),

            # Don't use Connect's custom backend as that would prevent
            # password reset messages from being sent to users who thought they
            # were simply unsubscribing from message notifications.
            connection=connection
        )
        message.attach_alternative(
            content=html_email,
            mimetype='text/html'
        )

        return message
