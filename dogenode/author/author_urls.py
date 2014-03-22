from django.conf.urls import patterns, url

from author import views

urlpatterns = patterns('',
    url(r'^profile/([-\w]+)/$', views.profile, name='profile'),
    url(r'^relationship/(\w+)/$', views.updateRelationship),
    url(r'^(?P<author_id>[-\w]+)/posts/$', views.getAuthorPosts),
    url(r'^stream/$', views.stream), 
    url(r'^friends/$', views.friends),
    url(r'^search_results/$', views.search),
    url(r'^edit_profile/$', views.editProfile),
)
