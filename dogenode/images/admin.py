from django.contrib import admin

from images.models import Image, ImageVisibilityException

admin.site.register(Image)
admin.site.register(ImageVisibilityException)
