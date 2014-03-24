from django.db import models
from author.models import Author
from categories.models import Category

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
        (SERVERONLY, "Dogenode friends only"),
        (PUBLIC, "Public"),
    )

    guid = models.CharField(max_length=36, unique=True, default=uuid.uuid4)
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

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
    
    def __unicode__(self):
        return "%i: [%s|%s|%s]" % (self.id, self.title, self.description, self.content)

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('post.views.handlePost', args=[self.guid])

    # TODO: Need to add admin logic.
    # TODO: Fix SERVERONLY logic
    def isAllowedToViewPost(self, author):
        # Check if post was created by the specified author
        if AuthorPost.objects.filter(post=self, author=author).count() > 0:
            return True
        # Check if post is public or server-only
        elif (self.visibility == Post.PUBLIC or 
              self.visibility == Post.SERVERONLY):
            return True
        # Check if this post's author is friends, and if the post is set to
        # friends-only or friends of friends
        elif (author in AuthorPost.objects.get(post=self).author.getFriends()
              and
              (self.visibility == Post.FRIENDS or 
               self.visibility == Post.FOAF)):
            return True
        # Check if this post's author is friends of friends with the specified
        # author, and if the post is set to friends of friends
        elif (author.isFriendOfAFriend(
                AuthorPost.objects.get(post=self).author)
              and self.visibility == Post.FOAF):
            return True
        # Check if the post has a visibility exception for the specified author
        elif (PostVisibilityException.objects.filter(post=self, 
                author=author).count() > 0):
            return True
        else:
            return False

    # TODO: Apparently I'm supposed to use some kind of Custom Manager for this...
    # See: https://docs.djangoproject.com/en/1.6/topics/db/managers/#django.db.models.Manager
    # Also, this way of doing things is VERY VERY VERY INEFFICIENT.
    @staticmethod
    def getAllowedPosts(author):
        posts = []
        # TODO: To save CPU cycles, can also check if a user is the admin.  If
        # so, return all the posts.
        for post in Post.objects.all().order_by('pubDate'):
            if post.isAllowedToViewPost(author):
                posts.insert(0, post)
        return posts

    # also inefficient, but w.e
    @staticmethod
    def getViewablePosts(viewer, author):
        """
        Returns all the posts of an author that a viewer can see
        """
        # Get all the posts that the viewer can see
        allposts = Post.getAllowedPosts(viewer)
        viewposts = []
        # Filter out all the posts that aren't by author
        for checkpost in allposts:
            if AuthorPost.objects.get(post=checkpost).author == author:
                viewposts.append(checkpost)
        return viewposts

# Removes Many-to-Many relationship between Posts and Categories
class PostCategory(models.Model):
    post = models.ForeignKey(Post)
    category = models.ForeignKey(Category)

    class Meta:
        verbose_name = 'Post Category'
        verbose_name_plural = 'Post Categories'

    def __unicode__(self):
        return "%i: [%i|%s]" % (self.id, self.post.id, str(self.category))

# Removes Many-to-Many relationship between Posts and Visibility Exception
class PostVisibilityException(models.Model):
    post = models.ForeignKey(Post)
    author = models.ForeignKey(Author)

    class Meta:
        verbose_name = 'Post Visibility Exception'
        verbose_name_plural = 'Post Visibility Exceptions'

    def __unicode__(self):
        return "%i: [%i|%s]" % (self.id, self.post.id, str(self.author))

# Removes Many-to-Many relationship between Authors and Posts
class AuthorPost(models.Model):
    author = models.ForeignKey(Author)
    post = models.ForeignKey(Post)

    class Meta:
        verbose_name = 'Author Post'
        verbose_name_plural = 'Author Posts'

    def __unicode__(self):
        return "%s | %s" % (str(self.author), str(self.post))
