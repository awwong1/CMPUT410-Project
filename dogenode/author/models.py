from django.db import models
from django.conf import settings

from django.contrib.auth.models import User
from django.db.models.signals import post_save

import uuid

# Create your models here.
class Author(models.Model):
    guid = models.CharField(max_length=36,
                                 unique=True, 
                                 default=uuid.uuid4)
    user = models.OneToOneField(User, primary_key=True)
    accepted = models.BooleanField(default=True)   
    host = models.CharField(max_length=100, default=settings.OUR_HOST)
    url = models.URLField(blank=True)
    githubUsername = models.CharField(max_length=128, blank=True)
    githubEventsETag = models.CharField(max_length=32, blank=True)

    def __unicode__(self):
        return self.user.username

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('author.views.profile', args=[self.guid])

    def as_dict(self):
        return {
            "id":self.guid,
            "displayname":self.user.username,
            "host": self.host,
            "url": self.url
        }

    def postGetFriendsFromList(self, author, authorList, host):

        headers = {"Content-type": "application/json"}
        postData = {
                        "query": "friends",
                        "author": author.guid,
                        "authors": authorList
                   }

        servers = AllowedServer.objects.all()

        if host in servers:

            try:
                response = requests.post('%sfriends/%s' % (host, author.guid),
                                         headers=headers,
                                         data=json.dumps(postData))
                response.raise_for_status() # Exception on 4XX/5XX response

                return response.json()["friends"]

            except requests.exceptions.RequestException:
                pass

        return []

    def getFriends(self):

        localRelationships = LocalRelationship.objects.filter(
                            (models.Q(author1=self) | models.Q(author2=self))
                            & models.Q(relationship=True))
        remoteRelationships = RemoteRelationship.objects.filter(
                            localAuthor=self, relationship=2)

        friends = { "local":[], "remote":[] }

        # Make the querysets into lists

        for r in localRelationships:
            if r.author1 == self:
                friends["local"].append(r.author2)
            else:
                friends["local"].append(r.author1)

        friends["remote"] = [r.remoteAuthor for r in remoteRelationships]

        return friends

    def getPendingSentRequests(self):

        localRelationships = LocalRelationship.objects.filter(author1=self,
                                                    relationship=False)
        remoteRelationships = RemoteRelationship.objects.filter(
                            localAuthor=self, relationship=0)

        return { "local":  [r.author2 for r in localRelationships],
                 "remote": [r.remoteAuthor for r in remoteRelationships] }

    def getPendingReceivedRequests(self):

        localRelationships = LocalRelationship.objects.filter(author2=self,
                                                    relationship=False)
        remoteRelationships = RemoteRelationship.objects.filter(
                            localAuthor=self, relationship=1)

        return { "local":  [r.author1 for r in localRelationships],
                 "remote": [r.remoteAuthor for r in remoteRelationships] }

    def isFriendOfAFriend(self, author, isRemote=False):

        selfFriends = self.getFriends()
        selfFriendsList = selfFriends["local"] + selfFriends["remote"]

        if isRemote:

            selfFriendsGUIDs = [f.guid for f in selfFriendsList]
            authorFriendsGUIDs = self.postGetFriendsFromList(author,
                                                             selfFriendsGUIDs,
                                                             author.host)

            if len(authorFriendsGUIDs) > 0:
                return True

        else:

            authorFriends = author.getFriends()
            authorFriendsList = (authorFriends["local"] +
                                 authorFriends["remote"])

            if set(selfFriendsList) & set(authorFriendsList):
                return True

        return False

# Create an Author automatically when a User is created
def createAuthor(sender, instance, created, **kwargs):
    if created:
        author, _ = Author.objects.get_or_create(user=instance)
        author.url = author.host + author.get_absolute_url() 
        author.save()

post_save.connect(createAuthor, sender=User, dispatch_uid="auto_create_author")

class RemoteAuthor(models.Model):

    guid = models.CharField(max_length=36,
                            unique=True,
                            default=uuid.uuid4)
    displayName = models.CharField(max_length=36)
    host = models.CharField(max_length=100, default="http://benhoboco/")
    url = models.URLField(blank=True)

    def __unicode__(self):
        return self.displayName

    # if the attributes for this guid changed, assume it was changed
    # on the remote server; update on our local server
    def update(self, displayName=None, host=None, url=None):

        self.displayName = displayName or self.displayName
        self.host = host or self.host
        self.url = url or self.url

        self.save()

class LocalRelationship(models.Model):

    author1 = models.ForeignKey(Author, related_name="author1")
    author2 = models.ForeignKey(Author, related_name="author2")

    # False means author1 has sent a friend request to author2 but
    # author2 has not accepted yet
    relationship = models.BooleanField(default=False)

class RemoteRelationship(models.Model):

    localAuthor = models.ForeignKey(Author, related_name="localAuthor")
    remoteAuthor = models.ForeignKey(RemoteAuthor)

    # 0 = localAuthor follows remoteAuthor
    # 1 = remoteAuthor follows localAuthor
    # 2 = localAuthor is friends with remoteAuthor
    relationship = models.PositiveSmallIntegerField(default=0)

