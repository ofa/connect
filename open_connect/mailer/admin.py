"""Django admin registration for Mailer Models"""

from django.contrib import admin

from open_connect.mailer.models import Unsubscribe

admin.site.register(Unsubscribe)
