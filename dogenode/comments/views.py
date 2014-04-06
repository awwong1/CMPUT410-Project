from django.shortcuts import render, redirect, render_to_response
from django.template import RequestContext
from django.http import HttpResponse

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from post.models import Post
from author.models import Author
from comments.models import Comment

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import json

# Create your views here.
def get_post_comments(request, post_id):
    """
    Displays all the comments based on postid
    Currently, nothing calls this
    """
    context = RequestContext(request)
    post = Post.objects.get(guid=post_id)
    comments = Comment.objects.filter(post_ref=post)
    context["comments"] = comments
    return render_to_response("fragments/post_content.html", context)

@api_view(['GET','POST','PUT'])
def add_comment(request):
    """
    Adds a comment to a post, redirects back to calling page
    """
    if request.user.is_authenticated():
        author = Author.objects.get(user=request.user)
        data = request.DATA
        post_id = data["post_id"]
        commentText = data["comment"]
        post = Post.objects.get(guid=post_id)
        comment = Comment.objects.create(
            author=author,
            comment=commentText,
            post_ref=post)
        jsonComment = comment.as_dict()
        jsonComment["postGuid"] = post_id
    return HttpResponse(json.dumps(jsonComment), 
                        status=status.HTTP_201_CREATED, 
                        content_type="application/json")

def remove_comment(request, comment_id):
    """
    Remove a comment, based on comment id
    Currently, nothing calls this
    """
    Comment.objects.get(id=comment_id).delete()
    return redirect(request.META['HTTP_REFERER'])
