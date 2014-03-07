from django.shortcuts import render, render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from post.models import Post
from author.models import Author
from comments.models import Comment
# Create your views here.

def posts(request):
    """
    Shows all the User's Posts
    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
        return render(request, 'login/index.html', context)

    author = Author.objects.filter(user=request.user)[0]    
    rawposts = Post.objects.filter(author=author).order_by('-date_created')
    comments = []
    for post in rawposts:
        comments.append(Comment.objects.filter(post_ref=post))
    context["posts"] = zip(rawposts, comments)

    return render_to_response('post/posts.html', context)

def post(request, post_id):
    """
    Returns a post and displays it in the web browser.
    """
    
    if request.user.is_authenticated():
        user = request.user
        author = Author.objects.get(user=request.user)   
        post = Post.objects.get(id=post_id)

        if (post.author == author):            
            context = RequestContext(request)
            comments = Comment.objects.filter(post_ref=post)
            context["posts"] = {post:comments}
            return render_to_response('post/post.html', context)

    else:
        return redirect('/login/')

def add_post(request):
    """
    Adds a new post and displays 
    """
    context = RequestContext(request)
   
    if request.method == "POST":
        content = request.POST.get("content", "")
        privacy = request.POST.get("privacy", "")
        allowed_readers = request.POST.get("others", "")
        post_format = request.POST.get("format", "")
    author = Author.objects.filter(user=request.user)[0]    
    Post.objects.create(content=content, author=author, privacy=privacy,
                                post_format=post_format) 
    posts = Post.objects.all()
    return redirect(request.META['HTTP_REFERER'])

def delete_post(request):
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
            post = Post.objects.get(id=post_id)
            if (post.author == author):
                # Delete post and its comments?
                post.delete();
            # else: send a message?

            return redirect('/posts/')
    else:
        return redirect('/login/')

def delete_comment():
    pass
