"""Application Configuration for the individualized version of Connect"""
from django.apps import AppConfig


class LocalConnectConfig(AppConfig):
    """App configuration for the individualized version of Connect"""
    name = 'private_connect'
    verbose_name = 'Private Connect'

    # pylint: disable=no-self-use
    def ready(self):
        """Functionality to execute with the app is ready"""
        # pylint: disable=unused-argument,unused-variable,wildcard-import
        from private_connect.signals import *
