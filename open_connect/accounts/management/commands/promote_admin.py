"""Command to set a user to have all admin permissions"""
from django.core.management.base import BaseCommand, CommandError

from open_connect.accounts.models import User
from open_connect.accounts.views import UpdateUserPermissionView


class Command(BaseCommand):
    """Command to set admin permissions for users"""
    help = "Give a user with a specified email address all admin permissions"
    def add_arguments(self, parser):
        parser.add_argument('user_email', nargs=1, type=str)

    def handle(self, *args, **options):
        """Handle command."""
        email = options['user_email'][0]

        try:
            user = User.objects.get(email=email)
        except:
            raise CommandError('User with email "%s" does not exist' % email)

        editable_permissions = UpdateUserPermissionView(
            ).get_editable_permissions()

        user.user_permissions = editable_permissions

        # User will be made staff
        user.is_staff = True

        user.save()

        self.stdout.write(
            'Successfully gave "%s" all admin permissions' % user)