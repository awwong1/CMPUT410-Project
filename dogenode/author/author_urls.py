from django.conf.urls import patterns, url

from author import views

urlpatterns = patterns('',
    url(r'^profile/(\w+)/$', views.profile, name='profile'),
    url(r'^posts/$', views.stream),
    url(r'^relationship/(\w+)/$', views.updateRelationship),
    url(r'^(?P<author_id>\d+)/posts/$', views.getAuthorPosts),
    url(r'^stream/$', views.stream), #don't need this anymore 
    url(r'^friends/$', views.friends),
    url(r'^friends/friendrequest$', views.sendFriendRequest),
    url(r'^friends/(\w+)$', views.getFriendsFromList),
    url(r'^friends/(\w+)+/(\w+)+/$', views.areFriends),
    url(r'^search_results/$', views.search),
    url(r'^edit_profile/$', views.editProfile),
)
