"""Application Configuration for the Accounts application"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """App configuration for the Accounts application"""
    name = 'open_connect.accounts'
    verbose_name = 'Accounts'

    # pylint: disable=no-self-use
    def ready(self):
        """Functionality to execute with the app is ready"""
        # pylint: disable=wildcard-import

        # We import our signals here to ensure they're attached to the correct
        # events.
        from open_connect.accounts.signals import *
