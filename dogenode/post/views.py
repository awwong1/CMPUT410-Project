from django.shortcuts import render, render_to_response
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from post.models import Post
from author.models import Author

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

    author = Author.objects.filter(user=request.user)[0]    
    Post.objects.get_or_create(content=content, author=author, privacy=privacy) 
    posts = Post.objects.all()

    return render_to_response('author/stream.html', {'posts':posts},  context)

def delete_post(request):
    pass



