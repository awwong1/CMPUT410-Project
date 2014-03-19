from django.conf.urls import patterns, url

from api import views

urlpatterns = patterns('',
    url(r'^friendrequest$', views.sendFriendRequest),
    url(r'^friends/(\w+)$', views.getFriendsFromList),
    url(r'^friends/(\w+)+/(\w+)+/$', views.areFriends),
)
