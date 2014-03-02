from django.conf.urls import patterns, url

from author import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^profile/$', views.profile, name='profile'),
    #url(r'^profile/(?P<author_name>\w+)/$', views.index, name='profile'),
    url(r'^profile/edit_profile$', views.edit_profile, name='edit_profile'),
    url(r'^posts$', views.posts, name='your_posts'),
    #url(r'^posts/?P<post_id>\w)/$', views.get_post, name='your_posts'),
    url(r'^friends$', views.friends, name='your_friends'),
    url(r'^search$', views.search, name='search_results'),
)
