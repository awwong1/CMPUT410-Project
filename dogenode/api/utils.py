from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from author.models import Author, LocalRelationship, RemoteRelationship
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory

from comments.models import Comment
from categories.models import Category
from api.serializers import AuthorSerializer, FullPostSerializer

import sys
import datetime
import json

def buildFullPost(rawposts):
    """
    Builds the full Post as a list of dictionaries as in example-article.json
    """
    # If there is only one Post
    if type(rawposts) is Post:
        return [buildFullPostContent(rawposts)]
    else:
        return [buildFullPostContent(post) for post in rawposts]

def serializeFullPost(posts):
    """
    Minor final Full Post cleanup to match example-article.json 
    """
    serializer = FullPostSerializer(posts, many=True)
    return {"posts":serializer.data}

def buildFullPostContent(post):
    """
    Bullds up one post dictionary from the Post Object for the post content 
    for the full response. Adds in the author, comments, categories 
    and visibility exceptions. Based on example-article.json 
    """
    # Post object
    postContent = post.as_dict()

    # Post Author Object
    author = AuthorPost.objects.get(post=post).author
    postContent["author"] = author.as_dict()

    # Comments for the Post
    comments = Comment.objects.filter(post_ref=post)
    postContent["comments"] = [c.as_dict() for c in comments]

    # Categories
    categoryIds = PostCategory.objects.filter(post=post).values_list(
        'category', flat=True)
    postContent["categories"] = Category.objects.filter(id__in=categoryIds)

    # Visibility exceptions: a list of author dictionaries
    otherAuthorIds = PostVisibilityException.objects.filter(
                        post=post).values_list('author', flat=True)
    othAuthors = Author.objects.filter(id__in=otherAuthorIds)
    otherAuthors = [auth.as_dict() for auth in othAuthors]
    postContent["visibilityExceptions"] = otherAuthors

    return postContent

