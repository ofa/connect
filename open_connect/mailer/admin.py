"""Django admin registration for Mailer Models"""

from django.contrib import admin

from open_connect.mailer.models import Unsubscribe


class UnsubscribeAdmin(admin.ModelAdmin):
    """Admin for Unsubscribes"""
    list_display = ('address', 'user', 'source')
    list_filter = ('source',)
    readonly_fields = [
        'user'
    ]
    search_fields = ['address']

    def get_queryset(self, request):
        """
        Get the queryset for the admin

        In order to reduce the number of hits to the database we can tell
        django to join in the `User` table when running the query that pulls in
        the Unsubscribes.
        """
        queryset = super(UnsubscribeAdmin, self).get_queryset(request)
        queryset = queryset.select_related('user')
        return queryset


admin.site.register(Unsubscribe, UnsubscribeAdmin)
