from django.conf.urls import patterns, include, url
from django.http import HttpResponseRedirect
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dogenode.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    # http://stackoverflow.com/a/7580365
    url(r'^$', lambda r : HttpResponseRedirect('author/stream/')),
    url(r'^login/', include('author.login_urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('comments.urls')),
    url(r'^posts/', include('post.urls')),
    url(r'^categories/', include('categories.urls')),
    url(r'^author/', include('author.author_urls')),
)
