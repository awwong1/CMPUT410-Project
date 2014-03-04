from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from Post.models import Post
# Create your views here.

def posts(request):
    """

    """
    context = RequestContext(request)
    
    return render(request, 'post/posts.html', context)

def post(request):
    """
    Returns a post and displays it
    """
    context = RequestContext(request)
    
    return render(request, 'post/post.html', context)

def add_post(request):
    """
    GET: retrieve post matching postid
    POST: create a new post
    DELETE: delete post
    """
    context = RequestContext(request)

    if request.method == "POST":
        content = request.POST.get("content", "")
        privacy = request.POST.get("privacy", "")
        allowed_readers = request.POST.get("others", "")
        format = request.POST.get("format", "")
    
    post = Post.objects.get_or_create()
 
    return render(request, 'post/stream.html', context)

def delete_post(request):
    pass



