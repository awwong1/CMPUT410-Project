from django.db import models

from django.contrib.auth.models import User
from django.db.models.signals import post_save

import uuid

# Create your models here.
class Author(models.Model):
    guid = models.CharField(max_length=36,
                                 unique=True, 
                                 default=uuid.uuid4)
    user = models.OneToOneField(User)
    accepted = models.BooleanField(default=False)   
    host = models.CharField(max_length=100, default="http://dogenode/")
    url = models.URLField(blank=True)

    def __unicode__(self):
        return self.user.username

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('author.views.profile', args=[self.guid])

    def getFriends(self):

        relationships = LocalRelationship.objects.filter(
                            (models.Q(author1=self) | models.Q(author2=self))
                            & models.Q(relationship=True))

        friends = []

        for r in relationships:
            if r.author1 == self:
                friends.append(r.author2)
            else:
                friends.append(r.author1)

        return friends

    def getPendingSentRequests(self):

        relationships = LocalRelationship.objects.filter(author1=self,
                                                    relationship=False)
        return [r.author2 for r in relationships]

    def getPendingReceivedRequests(self):

        relationships = LocalRelationship.objects.filter(author2=self,
                                                    relationship=False)
        return [r.author1 for r in relationships]

    def isFriendOfAFriend(self, author):

        if set(self.getFriends()) & set(author.getFriends()):
            return True

        return False


# Post-save stuff from:
# http://stackoverflow.com/questions/44109/extending-the-user-model-with-custom-fields-in-django
# Note: this is causing django to try and create a new author
# twice (even though dispatch_uid should prevent this), so this is
# being commented out.
#def addAcceptedAttribute(sender, instance, created, **kwargs):
#    if created:
#        _, _ = Author.objects.get_or_create(user=instance)

#post_save.connect(addAcceptedAttribute, sender=User,
#                  dispatch_uid="asdf")

class LocalRelationship(models.Model):

    author1 = models.ForeignKey(Author, related_name="author1")
    author2 = models.ForeignKey(Author, related_name="author2")

    # False means author1 has sent a friend request to author2 but
    # author2 has not accepted yet
    relationship = models.BooleanField(default=False)

class RemoteRelationship(models.Model):

    localAuthor = models.ForeignKey(Author, related_name="localAuthor")
    remoteAuthor = models.CharField(max_length=36,
                                    default=uuid.uuid4)
    # 0 = localAuthor follows remoteAuthor
    # 1 = remoteAuthor follows localAuthor
    # 2 = localAuthor is friends with remoteAuthor
    relationship = models.PositiveSmallIntegerField(default=0)

