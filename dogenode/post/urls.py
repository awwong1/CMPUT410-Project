from django.conf.urls import patterns, url

from post import views

urlpatterns = patterns('',
#    url(r'^author/(?P<author_id>\w+)/posts/$', views.posts),
#    url(r'^posts/(?P<post_id>\w+)/$', views.get_post),
#    url(r'^author/(?P<author_id>\w+)/posts/(?P<post_id>\w+)/$', views.friends),
     url(r'^$', views.posts),
     url(r'^post/$', views.post),
#     url(r'^posts/(?P<author_id>\w)/$', views.posts),

)
