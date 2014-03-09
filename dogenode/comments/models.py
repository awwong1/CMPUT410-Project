from django.db import models
from author.models import Author
from post.models import Post

import uuid

# Create your models here.
class Comment(models.Model):
    """
    This is the comment which links a user comment to a post
    """
    guid = models.CharField(max_length=36, default=uuid.uuid4())
    author = models.ForeignKey('author.Author')
    post_ref = models.ForeignKey('post.Post')
    comment = models.TextField()
    pub_date = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return "%i: [%s|%s|%s]"%(self.id,self.author,self.comment,
                                 self.pub_date)
