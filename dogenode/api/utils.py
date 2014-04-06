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
from images.models import Image, ImagePost

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
    postContent["categories"] = [c.name for c in Category.objects.filter(id__in=categoryIds)]

    # Visibility exceptions: a list of author dictionaries
    postExceptions = PostVisibilityException.objects.filter(post=post)
    otherAuthorIds = [exception.author.guid for exception in postExceptions]
    othAuthors = Author.objects.filter(guid__in=otherAuthorIds)
    otherAuthors = [auth.as_dict() for auth in othAuthors]
    postContent["visibilityExceptions"] = otherAuthors

    # Getting images
    imageIds = ImagePost.objects.filter(post=post).values_list(
                    'image', flat=True)
    images = Image.objects.filter(id__in=imageIds)
    postContent["images"] = [i.as_dict() for i in images]

    return postContent

