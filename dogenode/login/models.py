from django.db import models

from django.contrib.auth.models import User
from django.db.models.signals import post_save

# Create your models here.
class Author(models.Model):

    user = models.OneToOneField(User)
    accepted = models.BooleanField(default=False)

# Post-save stuff from:
# http://stackoverflow.com/questions/44109/extending-the-user-model-with-custom-fields-in-django
def addAcceptedAttribute(sender, instance, created, **kwargs):
    if created:
        _, _ = Author.objects.get_or_create(user=instance)

post_save.connect(addAcceptedAttribute, sender=User)
