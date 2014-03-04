from django.db import models

# Create your models here.
class Comment(models.Model):
    """
    This is the comment which links a user comment to a post
    """
    id = models.AutoField(primary_key=True)
    comment_auth = models.ForeignKey('author.Author')
    comment_text = models.TextField()
    #post_ref = models.ForeignKey('post.Post')
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    
