"""Django admin options for accounts models."""
from django.contrib import admin

from open_connect.accounts.actions import assign_to_perm_group
from open_connect.accounts.models import User
from open_connect.accounts.forms import UserAdminForm


class UserAdmin(admin.ModelAdmin):
    """Admin options for User model"""
    list_display = (
        'last_name',
        'first_name',
        'username',
        'date_joined',
        'last_login',
        'is_staff',
        'is_banned'
    )
    list_display_links = list_display
    list_filter = ('is_staff', 'is_banned')
    search_fields = ['last_name', 'email', 'username', 'first_name']
    actions = [assign_to_perm_group]
    exclude = (
        'password', 'is_superuser', 'groups', 'username', 'user_permissions')
    readonly_fields = ('last_login', 'date_joined', 'image')
    form = UserAdminForm

    def get_actions(self, request):
        """Get available actions for ModelAdmin"""
        actions = super(UserAdmin, self).get_actions(request)
        # Disable deleting a user in the admin
        del actions['delete_selected']
        return actions


admin.site.register(User, UserAdmin)
