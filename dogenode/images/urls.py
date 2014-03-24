from django.conf.urls import patterns, url

from images import views

urlpatterns = patterns('',
     url(r'^$', views.getViewableImages),
     url(r'^upload/$', views.uploadImage),
     url(r'^(?P<author_guid>[-\w]+)/$', views.getImagesByAuthor),
     url(r'^(?P<author_guid>[-\w]+)/(?P<image_name>[-\w\.]+)/$', views.getImage),
)
