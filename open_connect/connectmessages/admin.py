"""Django admin registration for connectmessages Models"""
from django.contrib import admin

from open_connect.connectmessages.models import Message, Thread

admin.site.register(Message)
admin.site.register(Thread)
