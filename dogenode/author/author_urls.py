from django.conf.urls import patterns, url

from author import views

urlpatterns = patterns('',
    url(r'^profile/(\w+)/$', views.profile, name='profile'),
    #url(r'^(?P<author_id>\w+)/$', views.profile),
    url(r'^relationship/(\w+)/$', views.updateRelationship),
    url(r'^stream/$', views.stream),
    #url(r'^(?P<author_id>\w)/stream/$', views.stream),  
    url(r'^friends/$', views.friends),
    #url(r'^(?P<author_id>\w)/friends/$', views.friends),
    url(r'^search_results/$', views.search),
    url(r'^posts/$', views.posts),
    #url(r'^(?P<author_id>\w)/posts/$', views.posts),
    #url(r'^posts/post/$', views.post),
    #url(r'^posts/(?P<post_id>\w)/$', views.post),
    url(r'^edit_profile/$', views.edit_profile),
)
