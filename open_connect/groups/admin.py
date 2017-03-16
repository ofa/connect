"""Admin functionality for group app"""
from django.contrib import admin
from django.contrib.auth.models import Group as AuthGroup

from open_connect.groups.models import Category


class CategoryAdmin(admin.ModelAdmin):
    """Admin for Group Categories"""
    readonly_fields = [
        'modified_at', 'created_at'
    ]


admin.site.register(Category, CategoryAdmin)


# Remove AuthGroup from the admin to prevent admins from being able to assign
# permissions to groups or otherwise edit groups in the admin.
admin.site.unregister(AuthGroup)
