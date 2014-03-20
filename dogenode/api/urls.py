from django.conf.urls import patterns, url

from api import views

urlpatterns = patterns('',
    url(r'^friendrequest$', views.sendFriendRequest),
    url(r'^friends/(\w+)$', views.getFriendsFromList),
    url(r'^friends/(\w+)+/(\w+)+$', views.areFriends),
    url(r'^posts/$', views.postsPublic),
    url(r'^post/(?P<pk>[0-9]+)/$', views.postSingle),
    url(r'^author/posts/$', views.getStream),
    url(r'^author/(?P<username>\w+)/$', views.authorProfile),
    url(r'^author/(?P<requestedUsername>\w+)/posts/$', views.getAuthorPosts),
)
