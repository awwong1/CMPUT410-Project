from django.db import models

# Create your models here.

# whitelist
class AllowedServer(models.Model):
    name = models.CharField(max_length=50, blank=True)
    host = models.CharField(max_length=100, default="http://127.0.0.1:8000/")
