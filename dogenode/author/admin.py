from django.contrib import admin

from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from author.models import Author, Relationship

# Register your models here.

class AuthorInline(admin.StackedInline):
    model = Author

class UserAdmin(UserAdmin):

    def isAccepted(self, user):
        author = Author.objects.filter(user=user)
        if len(author) > 0:
            return author[0].accepted

        return False

    def displayName(self, user):
        author = Author.objects.filter(user=user)
        self.short_description = "hiiii"
        if len(author) > 0:
            author[0].displayName = user.username
            author[0].save()
        return user.username

    isAccepted.boolean = True
    isAccepted.short_description = "Accepted"

    list_display = ('username', 'displayName', 'first_name', 'last_name', 'email',
                    'isAccepted')
    inlines = (AuthorInline, )

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Relationship)
admin.site.register(Author)
