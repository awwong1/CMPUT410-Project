from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dogenode.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^login/', include('login.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^author/', include('author.urls')),
    url(r'^post/', include('post.urls')),
)
