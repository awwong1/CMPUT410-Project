from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=80)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('categories.views.category', args=[str(self.id)])
