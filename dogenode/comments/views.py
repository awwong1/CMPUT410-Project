from django.shortcuts import render, redirect
from django.template import RequestContext
from django.http import HttpResponse

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from post.models import Post
from author.models import Author
from comments.models import Comment

# Create your views here.
def get_post_comments(request, post_id):
    """
    Displays all the comments based on postid
    Currently, nothing calls this
    """
    context = RequestContext(request)
    post = Post.objects.get(id=post_id)
    comments = Comment.objects.filter(post_ref=post)
    context["posts"]={post:comments}
    return render_to_response("fragments/post_content.html", context)

def add_comment(request):
    """
    Adds a comment to a post, redirects back to calling page
    """
    if request.method == "POST" and request.user.is_authenticated():
        author = Author.objects.get(user=request.user)
        post_id = request.POST['post_id']
        commentText = request.POST['newComment']
        post = Post.objects.get(id=post_id)
        Comment.objects.create(
            comment_auth=author,
            comment_text=commentText,
            post_ref=post)
    return redirect(request.META['HTTP_REFERER'])
