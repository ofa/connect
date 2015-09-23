"""Admin functionality for media app models"""

from django.contrib import admin

from open_connect.media.models import Image

admin.site.register(Image)
