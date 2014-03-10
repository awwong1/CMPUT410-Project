from django.conf.urls import patterns, url

from categories import views

urlpatterns = patterns('',
    url(r'^$', views.categories),
    url(r'^(?P<category_id>\d+)/$', views.category),
    url(r'^add$', views.add),
)
