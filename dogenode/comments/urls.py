from django.conf.urls import patterns, url

from comments import views

urlpatterns = patterns('',
    url(r'^add_comment/$', views.add_comment),
)
