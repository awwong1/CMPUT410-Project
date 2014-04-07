from django.conf import settings
from django.db import models
from author.models import Author
from categories.models import Category
from datetime import *
from dateutil.tz import *
from urlparse import urljoin

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

    guid = models.CharField(max_length=36, unique=True)
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
        return reverse('post.views.getPost', args=[self.guid])

    def as_dict(self):
        return {
            'guid' : self.guid,
            'title' : self.title,
            'description' : self.description,
            'content' : self.content,
            'visibility': self.visibility,
            'content-type' : self.contentType,
            'origin' : self.origin,
            'pubDate' : self.__datetimeToJSONString(self.pubDate),
            'modifiedDate' : self.__datetimeToJSONString(self.modifiedDate),
            'source' : urljoin(settings.OUR_HOST, self.get_absolute_url()),
            'HTML' : self.HTML,
            'PLAIN' : self.PLAIN,
            'MARKDOWN' : self.MARKDOWN
        }

    def __datetimeToJSONString(self, dt):
        mstDatetime = dt.astimezone(gettz("MST"))
        ctime = mstDatetime.ctime()
        return ctime[:-4] + "MST " + ctime[-4:] # So dirty

    # Pass in an Author object, and this function will check if the Post
    # instance is viewable by the author.
    # Pass in a True checkFollow flag, and this function will return True for
    # public posts that were written by the viewer's followed authors.  Else,
    # any public post returns True.
    # TODO: Need to add admin logic.
    def isAllowedToViewPost(self, viewer, checkFollow=False):
        if viewer.user.is_staff:
            return True

        postAuthor = AuthorPost.objects.get(post=self).author
        
        friends = viewer.getFriends()
        followed = viewer.getPendingSentRequests()
        # Check if post was created by the specified viewer
        if AuthorPost.objects.filter(post=self, author=viewer).count() > 0:
            return True
        # Check if the post has a visibility exception for the viewer
        elif (PostVisibilityException.objects.filter(post=self,
                author=viewer).count() > 0):
            return True
        # Check if this post's author is friends with the viewer
        elif postAuthor in friends['local'] or postAuthor in friends['remote']:
            if (self.visibility == Post.FRIENDS or
                    self.visibility == Post.FOAF or
                    self.visibility == Post.PUBLIC):
                return True
            elif self.visibility == Post.SERVERONLY:
                if postAuthor in friends['local']:
                    return True
                # SERVERONLY disallows remote viewers from viewing this post
                else:
                    return False
        # Check if this post's author is friends of friends with the viewer,
        # and if the post is set to friends of friends
        elif (viewer.isFriendOfAFriend(postAuthor)
              and self.visibility == Post.FOAF):
            return True
        # Check if post is public, and if necessary, if post is by someone the
        # viewer is following.
        elif self.visibility == Post.PUBLIC:
            if not checkFollow:
                return True
            elif (postAuthor in followed['local'] or
                  postAuthor in followed['remote']):
                return True
            else:
                return False
        else:
            return False

    # TODO: Apparently I'm supposed to use some kind of Custom Manager for this...
    # See: https://docs.djangoproject.com/en/1.6/topics/db/managers/#django.db.models.Manager
    # checkFollow is set to False if you want to get every single post a user
    # can see, based on visibility.  Set it to True if out of all public posts,
    # you only want posts from authors the user follows.
    # Also, this way of doing things is VERY VERY VERY INEFFICIENT.
    @staticmethod
    def getAllowedPosts(author, checkFollow=False):
        posts = []
        followed = author.getPendingSentRequests()
        allPosts = Post.objects.all().order_by('-pubDate')

        # TODO: In here, we probably need to make remote calls to get posts from
        #       other servers.

        # Staff-level users can see every post
        if author.user.is_staff:
            # Remember to also get remote posts
            return allPosts

        for post in allPosts:
            postAuthor = AuthorPost.objects.get(post=post).author
            if post.isAllowedToViewPost(author, checkFollow):
                posts.append(post)
        return posts

    @staticmethod
    def getViewablePosts(viewer, author):
        """
        Returns all the posts of an author that the viewer can see
        """
        postIds = AuthorPost.objects.filter(author=author).values_list(
                            'post', flat=True)
        postsByAuthor = Post.objects.filter(id__in=postIds).order_by(
                            '-pubDate')
        viewablePosts = []

        # Check if viewer can view this author's post
        for post in postsByAuthor:
            if post.isAllowedToViewPost(viewer):
                viewablePosts.append(post)

        return viewablePosts

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
