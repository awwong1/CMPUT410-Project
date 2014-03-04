from django.db import models
from author.models import Author

# Create your models here.
class Post(models.Model):
    id = models.AutoField(primary_key=True)
    author = models.ForeignKey("author.Author")
    content = models.TextField()
    privacy = models.CharField(max_length=32)
    #privacy_exceptions = models.ManyToManyField("author.Author")
    post_format = models.CharField(max_length=16)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    
    def __str__(self):
        return self.content
