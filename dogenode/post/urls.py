from django.conf.urls import patterns, url

from post import views

urlpatterns = patterns('',
#    url(r'^author/(?P<author_id>\w+)/posts/$', views.posts),
#    url(r'^author/(?P<author_id>\w+)/posts/(?P<post_id>\w+)/$', views.friends),
     url(r'^$', views.getAllPublicPosts),
     url(r'^(?P<post_id>\d+)/$', views.handlePost),
     url(r'^add_post/$', views.addFormPost),
     url(r'^delete_post/$', views.deletePost),
)
