from django.conf.urls import patterns, url

from api import views

urlpatterns = patterns('',
    url(r'^search$', views.search),
    url(r'^posts/$', views.getPublicPosts),
    url(r'^post/([-\w]+)$', views.postSingle),
    url(r'^author/posts$', views.getStream),
    url(r'^author/(?P<authorId>[-\w]+)$', views.authorProfile),
    url(r'^author/(?P<requestedAuthorId>[-\w]+)/posts$', views.getAuthorPostsAsJSON),
)
