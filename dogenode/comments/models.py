from django.db import models
from author.models import Author
from post.models import Post
from datetime import *
from dateutil.tz import *

import uuid

# Create your models here.
class Comment(models.Model):
    """
    This is the comment which links a user comment to a post
    """
    guid = models.CharField(max_length=36, default=uuid.uuid4)
    author = models.ForeignKey('author.Author')
    post_ref = models.ForeignKey('post.Post')
    comment = models.TextField()
    pubDate = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return "%i: [%s|%s|%s]"%(self.id,self.author,self.comment,
                                 self.pubDate)

    def as_dict(self):
        return {
            "guid": str(self.guid),
            "author": self.author.as_dict(),
            "comment": self.comment,
            "pubDate": self.__datetimeToJSONString(self.pubDate)
        }

    def __datetimeToJSONString(self, dt):
        mstDatetime = dt.astimezone(gettz("MST"))
        ctime = mstDatetime.ctime()
        return ctime[:-4] + "MST " + ctime[-4:] # So dirty
