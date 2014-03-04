from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dogenode.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^login/', include('author.login_urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^posts/', include('post.urls')),
    url(r'^author/', include('author.author_urls')),
)
