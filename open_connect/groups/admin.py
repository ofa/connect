"""Admin functionality for group app"""
from django.contrib import admin

from open_connect.groups.models import Category


class CategoryAdmin(admin.ModelAdmin):
    """Admin for Group Categories"""
    readonly_fields = [
        'modified_at', 'created_at'
    ]


admin.site.register(Category, CategoryAdmin)
