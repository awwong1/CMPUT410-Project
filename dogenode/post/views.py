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
    Shows all the User's Posts
    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
        return render(request, 'login/index.html', context)

    author = Author.objects.filter(user=request.user)[0]    

    posts = Post.objects.filter(author=author)

    context = RequestContext(request, 
                    { "posts" : posts })

    return render_to_response('post/posts.html', context)

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
        post_format = request.POST.get("format", "")

    author = Author.objects.filter(user=request.user)[0]    
    Post.objects.get_or_create(content=content, author=author, privacy=privacy,
                                post_format=post_format) 
    posts = Post.objects.all()

    return render_to_response('author/stream.html', {'posts':posts},  context)

def delete_post(request):
    """
    Deletes the Post based on the post id given in the request.
    Returns the user back to their posts page.
    """
    pass
