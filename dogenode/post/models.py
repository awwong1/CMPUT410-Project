from django.db import models
from author.models import Author

import uuid

# Create your models here.
class Post(models.Model):
    PLAIN = "text/plain"
    HTML = "text/html"
    MARKDOWN = "text/x-markdown"
    CONTENT_TYPE_CHOICES = (
        (PLAIN, "Plain"),
        (HTML, "HTML"),
        (MARKDOWN, "Markdown"),
    )

    PRIVATE = "PRIVATE"
    FRIENDS = "FRIENDS"
    FOAF = "FOAF"
    SERVERONLY = "SERVERONLY"
    PUBLIC = "PUBLIC"
    VISIBILITY_CHOICES = (
        (PRIVATE, "Private"),
        (FRIENDS, "Friends only"),
        (FOAF, "Friends of friends"),
        (SERVERONLY, "Dogenode only"),
        (PUBLIC, "Public"),
    )

    guid = models.CharField(max_length=36, default=uuid.uuid4())
    title = models.CharField(max_length=140, blank=True)
    description = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    visibility = models.CharField(max_length=10, 
                                  choices=VISIBILITY_CHOICES, 
                                  default=PRIVATE)
    contentType = models.CharField(max_length=15, 
                                    choices=CONTENT_TYPE_CHOICES, 
                                    default=PLAIN)
    origin = models.URLField(blank=True)
    pubDate = models.DateTimeField(auto_now_add=True)
    modifiedDate = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return "%i: [%s|%s|%s]" % (self.id, self.title, self.description, self.content)

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('post.views.post', args=[str(self.id)])

    # TODO: Need to add FOAF logic.  I'm assuming Author model will have some
    #       sort of method for this eventually.
    def isAllowedToViewPost(self, author):
        if AuthorPost.objects.filter(post=self, author=author).count() > 0:
            return True
        elif self.visibility == Post.PUBLIC or self.visibility == Post.SERVERONLY:
            return True
        elif (author in AuthorPost.objects.get(post=self).author.getFriends() and
              (self.visibility == Post.FRIENDS or self.visibility == Post.FOAF)):
            return True
        elif PostVisibilityException.objects.filter(post=self, author=author).count() > 0:
            return True
        else:
            return False

    # TODO: Apparently I'm supposed to use some kind of Custom Manager for this...
    # See: https://docs.djangoproject.com/en/1.6/topics/db/managers/#django.db.models.Manager
    # Also, this way of doing things is VERY VERY VERY INEFFICIENT.
    @staticmethod
    def getAllowedPosts(author):
        posts = []
        for post in Post.objects.all().order_by('pubDate'):
            if post.isAllowedToViewPost(author):
                posts.insert(0, post)
        return posts

class Category(models.Model):
    name = models.CharField(max_length=80)

    def __unicode__(self):
        return self.name

# Removes Many-to-Many relationship between Posts and Categories
class PostCategory(models.Model):
    post = models.ForeignKey(Post)
    category = models.ForeignKey(Category)

    def __unicode__(self):
        return "%i: [%i|%s]" % (self.id, self.post.id, str(self.category))

# Removes Many-to-Many relationship between Posts and Visibility Exception
class PostVisibilityException(models.Model):
    post = models.ForeignKey(Post)
    author = models.ForeignKey(Author)

    def __unicode__(self):
        return "%i: [%i|%s]" % (self.id, self.post.id, str(self.author))

# Removes Many-to-Many relationship between Authors and Posts
class AuthorPost(models.Model):
    author = models.ForeignKey(Author)
    post = models.ForeignKey(Post)

    def __unicode__(self):
        return "%s | %s" % (str(self.author), str(self.post))
