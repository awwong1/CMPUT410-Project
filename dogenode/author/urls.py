from django.conf.urls import patterns, url

from author import views

urlpatterns = patterns('',
    url(r'^$', views.index),
    url(r'^stream/$', views.stream),
    #url(r'^profile/(?P<author_name>\w+)/$', views.get_author),
    url(r'^profile/edit_profile$', views.edit_profile),
    url(r'^posts/$', views.posts),
    #url(r'^posts/?P<post_id>\w)/$', views.get_post),
    url(r'^friends/$', views.friends),
    url(r'^search_results/$', views.search),
)
