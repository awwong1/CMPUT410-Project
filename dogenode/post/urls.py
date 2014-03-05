from django.conf.urls import patterns, url

from post import views

urlpatterns = patterns('',
#    url(r'^author/(?P<author_id>\w+)/posts/$', views.posts),
#    url(r'^author/(?P<author_id>\w+)/posts/(?P<post_id>\w+)/$', views.friends),
     url(r'^$', views.posts),
     url(r'^post/$', views.post),
     url(r'^(?P<post_id>\w+)/$', views.post),
     url(r'^add_post/$', views.add_post),
     url(r'^delete_post/$', views.delete_post),
#     url(r'^posts/(?P<author_id>\w)/$', views.posts),

)
