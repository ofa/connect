"""Admin functionality for group app"""
from django.contrib import admin

from open_connect.groups.models import Group, Category


class GroupAdmin(admin.ModelAdmin):
    """Admin functionality for Application Groups"""
    list_filter = ('state', 'is_national', 'category')
    search_fields = ('group__name',)
    readonly_fields = [
        'group', 'owners', 'whitelist_users', 'created_by',
        'status', 'tos_accepted_at', 'image', 'tags'
    ]


class CategoryAdmin(admin.ModelAdmin):
    """Admin for Group Categories"""
    readonly_fields = [
        'modified_at', 'created_at'
    ]


admin.site.register(Group, GroupAdmin)
admin.site.register(Category, CategoryAdmin)
