from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from django.views.decorators.csrf import ensure_csrf_cookie

from api.utils import *
from api.views import *
from author.models import Author, RemoteAuthor
from categories.models import Category
from comments.models import Comment
from images.models import Image, ImagePost, ImageVisibilityException
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory

import datetime
import markdown
import requests

"""
NOTE: All API-related functionality resides in api.views, the functions in
      post.views pass the request on to the proper functions in api.views.
"""

def getPost(request, post_id):
    """
    Returns a post and displays it in the web browser if the request
    be accessed by http://service/post/{post_id}, which would return a list
    of posts containing the requested post. If the currently authenticated
    user does not have the permission to view the post, the list will be
    empty.
    """
    if 'application/json' in request.META['HTTP_ACCEPT']:
        return postSingle(request, post_id)
    elif 'text/html' in request.META['HTTP_ACCEPT']:
        if request.user.is_authenticated():
            user = request.user
            author = Author.objects.get(user=request.user)
            post = Post.objects.get(guid=post_id)
            if (post.isAllowedToViewPost(author)):
                context = RequestContext(request)
                components = getPostComponents(post) # From api.utils

                # Convert Markdown into HTML for web browser
                # django.contrib.markup is deprecated in 1.6, so, workaround
                if post.contentType == post.MARKDOWN:
                    post.content = markdown.markdown(post.content)

                context['posts'] = [(post, components["postAuthor"],
                                    components["comments"],
                                    components["categories"],
                                    components["visibilityExceptions"],
                                    components["images"])]
                context['author_id'] = author.guid

                return render_to_response('post/post.html', context)
        else:
            return redirect('/login/')
    else:
        return postSingle(request, post_id)

def getAllPublicPosts(request):
    """
    Retrieves all public posts
    """
    if 'application/json' in request.META['HTTP_ACCEPT']:
        return getPublicPosts(request)
    if 'text/html' in request.META['HTTP_ACCEPT'] and request.user.is_authenticated():
        # must be logged in to see stream in fancy html mode, but not get public json
        context = RequestContext(request)
        author = Author.objects.get(user=request.user)
        rawposts = Post.objects.filter(visibility=Post.PUBLIC)
        comments = []
        authors = []
        categories = []
        visibilityExceptions = []
        images = []

        for post in rawposts:
            categoryIds = PostCategory.objects.filter(post=post).values_list(
                'category', flat=True)
            authorIds = PostVisibilityException.objects.filter(
                post=post).values_list('author', flat=True)
            imageIds = ImagePost.objects.filter(post=post).values_list(
                'image', flat=True)
            
            authors.append(AuthorPost.objects.get(post=post).author)
            comments.append(Comment.objects.filter(post_ref=post))
            categories.append(Category.objects.filter(id__in=categoryIds))
            visibilityExceptions.append(Author.objects.filter(
                    guid__in=authorIds))
            images.append(Image.objects.filter(id__in=imageIds))

        # Stream payload
        serverPosts = zip(rawposts, authors, comments, categories, 
                          visibilityExceptions, images)
        externalPosts = []
        # Get the other server posts:                                       
        servers = AllowedServer.objects.all()
        
        for server in servers:
            try:
                # another hack because what the heck is going on with /api/
                if server.host == 'http://127.0.0.1:80/':
                    response = requests.get(
                        "{0}api/posts".format(server.host))
                else:
                    response = requests.get(
                        "{0}posts".format(server.host))
                response.raise_for_status()
                jsonAllPosts = response.json()['posts']
                # turn into a dummy post                                    
                for jsonPost in jsonAllPosts:
                    externalPosts.append(jsonPost)
            except Exception as e:
                # print ("failed to get posts from {1},\n{0}".format(e, server))
                # May cause IO error, commented out for stability
                pass
            
        for externalPost in externalPosts:
            parsedPost = rawPostViewConverter(externalPost)
            if parsedPost != None:
                serverPosts.append(parsedPost)
        
        context['posts'] = serverPosts
        context['visibilities'] = Post.VISIBILITY_CHOICES
        context['contentTypes'] = Post.CONTENT_TYPE_CHOICES
        context['author_id'] = author.guid
        return render_to_response('post/public_posts.html', context)
    
    elif 'text/html' in request.META['HTTP_ACCEPT']:
        return redirect('/')
    else:
        return getPublicPosts(request)

def deletePost(request):
    """
    Deletes the Post based on the post id given in the request.
    Returns the user back to their posts page.
    """
    if request.user.is_authenticated():
        context = RequestContext(request)
        user = request.user
        author = Author.objects.get(user=request.user)
        if request.method == "POST":
            post_id = request.POST["post_id"]
            post = Post.objects.get(guid=post_id)
            comments = Comment.objects.filter(post_ref=post)

            if (AuthorPost.objects.filter(post=post,
                                          author=author).count() > 0):
                comments.delete();
                post.delete();
            # else: send a message?

        return redirect('/author/'+str(author.guid)+'/posts/')
    else:
        return redirect('/login/')
