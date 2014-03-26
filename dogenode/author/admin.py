from django.contrib import admin

from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from author.models import Author, LocalRelationship

# Register your models here.

class AuthorInline(admin.StackedInline):
    model = Author

class UserAdmin(UserAdmin):

    def isAccepted(self, user):
        author = Author.objects.filter(user=user)
        if len(author) > 0:
            return author[0].accepted

        return False

    isAccepted.boolean = True
    isAccepted.short_description = "Accepted"

    list_display = ('username', 'first_name', 'last_name', 'email',
                    'isAccepted')
    inlines = (AuthorInline, )

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(LocalRelationship)
admin.site.register(Author)
