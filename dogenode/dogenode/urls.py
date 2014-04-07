from django.conf.urls import patterns, include, url
from django.http import HttpResponseRedirect
from django.contrib import admin

from api import views
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dogenode.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    # http://stackoverflow.com/a/7580365
    url(r'^$', lambda r : HttpResponseRedirect('author/stream/')),
    url(r'^friendrequest$', views.sendFriendRequest),
    url(r'^friends/([\w|-]+)$', views.getFriendsFromList),
    url(r'^friends/([\w|-]+)+/([\w|-]+)+$', views.areFriends),
    url(r'^login/', include('author.login_urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('comments.urls')),
    url(r'^posts/', include('post.urls')),
    url(r'^images/', include('images.urls')),
    url(r'^categories/', include('categories.urls')),
    url(r'^author/', include('author.author_urls')),
    url(r'^api/', include('api.urls')),
    url(r'^api-auth/', include('rest_framework.urls', 
        namespace='rest_framework'))
)
