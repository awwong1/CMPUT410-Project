import os
from django.conf import settings
from django.db.models.signals import post_delete
from django.db import models
from author.models import Author
from post.models import Post
from urlparse import urljoin

def useAuthorGuid(instance, filename):
    return os.path.join(instance.author.guid, filename)

# Image wrapper model to enforce visibility constraints.
# This shares a lot of code with the Post model, so if you change anything in
# isAllowedToViewPost/Image, getAllowedPosts/Images, getViewablePosts/Images,
# change the counterpart too.
class Image(models.Model):
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

    author = models.ForeignKey(Author)
    file = models.ImageField(upload_to=useAuthorGuid)
    visibility = models.CharField(max_length=10, 
                                  choices=VISIBILITY_CHOICES, 
                                  default=PRIVATE)
    contentType = models.CharField(max_length=40)

    def __unicode__(self):
        return self.file.name

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.file.name,
            "url": urljoin(settings.OUR_HOST, self.get_absolute_url()),
            "visibility": self.visibility
        }

    def get_absolute_url(self):
        return self.file.url

    # After DB delete, delete the image from filesystem, as well as
    # deleting the author's folder if empty.
    @staticmethod
    def post_delete_callback(sender, instance, **kwargs):
        imagePath = os.path.abspath(os.path.join(
                                        settings.MEDIA_ROOT, instance.file.name))
        mediaPath = os.path.abspath(os.path.join(
                                        settings.MEDIA_ROOT, instance.author.guid))

        try:
            os.remove(imagePath)
            os.rmdir(mediaPath)
        except OSError:
            pass

    # TODO: Need to add admin logic.
    # TODO: Fix SERVERONLY logic
    def isAllowedToViewImage(self, author):
        # Check if image was uploaded by the specified author
        if self.author == author:
            return True
        # Check if image is public or server-only
        elif (self.visibility == Image.PUBLIC or 
              self.visibility == Image.SERVERONLY):
            return True
        # Check if this image's author is friends, and if the image is set to
        # friends-only or friends of friends
        elif (self.author in author.getFriends()
              and
              (self.visibility == Image.FRIENDS or 
               self.visibility == Image.FOAF)):
            return True
        # Check if this image's author is friends of friends with the specified
        # author, and if the image is set to friends of friends
        elif (author.isFriendOfAFriend(self.author)
              and self.visibility == Image.FOAF):
            return True
        # Check if the image has a visibility exception for the specified author
        elif (ImageVisibilityException.objects.filter(image=self, 
                author=author).count() > 0):
            return True
        else:
            return False

    # TODO: Apparently I'm supposed to use some kind of Custom Manager for this...
    # See: https://docs.djangoproject.com/en/1.6/topics/db/managers/#django.db.models.Manager
    # Also, this way of doing things is VERY VERY VERY INEFFICIENT.
    @staticmethod
    def getAllowedImages(author):
        images = []
        # TODO: To save CPU cycles, can also check if a user is the admin.  If
        # so, return all the images.
        for image in Image.objects.all():
            if image.isAllowedToViewImage(author):
                images.insert(0, image)
        return image

    # TODO: Should filter on author instead of calling getAllowedImages
    @staticmethod
    def getViewableImages(viewer, author):
        """
        Returns all the images of an author that a viewer can see
        """
        # Get all the images that the viewer can see
        allImages = Image.getAllowedImages(viewer)
        viewImages = []
        # Filter out all the images that aren't by author
        for image in allImages:
            if image.author == author:
                viewImages.append(image)
        return viewImages


class ImageVisibilityException(models.Model):
    image = models.ForeignKey(Image)
    author = models.ForeignKey(Author)

    class Meta:
        verbose_name = 'Image Visibility Exception'
        verbose_name_plural = 'Image Visibility Exceptions'

    def __unicode__(self):
        return "%i: [%s|%s]" % (self.id, str(self.image), str(self.author))


class ImagePost(models.Model):
    image = models.ForeignKey(Image)
    post = models.ForeignKey(Post)

    class Meta:
        verbose_name = 'Image Post'
        verbose_name_plural = 'Image Posts'

    def __unicode__(self):
        return "%i: [%s|%s]" % (self.id, str(self.image), str(self.post))


post_delete.connect(Image.post_delete_callback, sender=Image)
