from django.conf.urls import patterns, url

from comments import views

urlpatterns = patterns('',
    url(r'^add_comment/$', views.add_comment),
    url(r'^remove_comment/(?P<comment_id>\d+)/$', views.remove_comment),
    url(r'^(?P<post_id>[-\w]+)/$', views.get_post_comments),
)
