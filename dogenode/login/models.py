from django.db import models

# Create your models here.
class Author(models.Model):

    username = models.CharField(max_length=20)
    #TODO: password should be hashed and salted (mmm...)
    password = models.CharField(max_length=20)

    def __unicode__(self):
        return self.username

    # This is redundant right now (just used for making a unit test)
    # We may need this later to unhash our passwords
    def getPassword(self):
        return self.password
