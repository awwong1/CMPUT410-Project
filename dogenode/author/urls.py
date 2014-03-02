from django.conf.urls import patterns, url

from author import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
)
