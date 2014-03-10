from django.contrib import admin

from post.models import Post, PostVisibilityException, AuthorPost, PostCategory

# Register your models here.

admin.site.register(Post)
admin.site.register(PostVisibilityException)
admin.site.register(AuthorPost)
admin.site.register(PostCategory)
