from django.conf.urls import patterns, url

from author import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^register/$', views.register, name='register'),
    url(r'^friends/$', views.friends, name='friends'),
)
