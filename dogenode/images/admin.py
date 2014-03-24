from django.contrib import admin

from images.models import Image, ImagePost, ImageVisibilityException

admin.site.register(Image)
admin.site.register(ImagePost)
admin.site.register(ImageVisibilityException)
