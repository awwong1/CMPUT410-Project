from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from author.models import Author, LocalRelationship, RemoteRelationship
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from post.views import createPost, updatePost

from comments.models import Comment
from categories.models import Category
from api.serializers import AuthorSerializer, FullPostSerializer
from api.utils import *

import sys
import datetime
import json
import urllib, urllib2

# List of other servers we are communicating with
SERVER_URLS = ['http://127.0.0.1:8001/' #BenHoboCo
              ]

#TODO: find a way to get this value automatically
OURHOST = "http://127.0.0.1:8000/"

#TODO: not sure where best to put this POST request (authors/views uses it too)
def postFriendRequest(localAuthor, remoteAuthor):

    postData = {
                    "query":"friendrequest",
                    "author":{
                        "id":localAuthor.guid,
                        "host":OURHOST,
                        "displayname":localAuthor.user.username
                    },
                    "friend":{
                        "author":{
                            "id":remoteAuthor.guid,
                            "host":remoteAuthor.host,
                            "displayname":remoteAuthor.displayName,
                            "url":remoteAuthor.url
                        }
                    }
                }

    #TODO: this needs to be customized for each remote server
    if remoteAuthor.host == SERVER_URLS[0]:
        try:
            result = urllib2.urlopen(
                        '%s/api/authors/%s/friends/' %
                                 (SERVER_URLS[0],
                                  remoteAuthor.displayName),
                         urllib.urlencode(postData))
        except urllib2.URLError:
            #TODO: we should really let the user know the remote server
            # is down
            pass

def areFriends(request, guid1, guid2):

    response = {"query":"friends",
                "friends":"NO"}

    if request.method == 'POST':

        author1 = Author.objects.filter(guid=guid1)
        author2 = Author.objects.filter(guid=guid2)

        # Both authors are local
        if len(author1) > 0 and len(author2) > 0:

            author1 = author1[0]
            author2 = author2[0]

            if author2 in author1.getFriends()["local"]:
                response["friends"] = [guid1, guid2]

        # author1 is local, author2 is remote
        elif len(author1) > 0 and len(author2) == 0:

            author1 = author1[0]
            remoteFriendGUIDs = [a.guid for a in author1.getFriends()["remote"]]

            if guid2 in remoteFriendGUIDs:
                response["friends"] = [guid1, guid2]

        # author1 is remote, author2 is local
        elif len(author1) == 0 and len(author2) > 0:

            author2 = author2[0]

            remoteFriendGUIDs = [a.guid for a in author2.getFriends()["remote"]]

            if guid1 in remoteFriendGUIDs:
                response["friends"] = [guid1, guid2]


    return HttpResponse(json.dumps(response),
                        content_type="application/json")

# The POST request is sent to a url which includes the user ID, but the user
# ID is also sent in the POST request body.
# Right now I am using the user ID sent in the request body
def getFriendsFromList(request, guid):

    response = {"query":"friends",
                "author":guid,
                "friends":[]}

    if request.method == 'POST':

        jsonData = json.loads(request.body)

        guid = jsonData['author']
        author = Author.objects.filter(guid=guid)

        if len(author) > 0:

            author = author[0]

            authorFriends = author.getFriends()

            localFriendGUIDs = [a.guid for a in authorFriends["local"]]
            remoteFriendGUIDs = [a.guid for a in authorFriends["remote"]]

            allFriendGUIDs = localFriendGUIDs + remoteFriendGUIDs

            friends = list(set(allFriendGUIDs) & set(jsonData["authors"]))
            
            response["author"] = guid
            response["friends"] = friends

    return HttpResponse(json.dumps(response),
                        content_type="application/json")

#TODO: lots of repeated code, I'll need to refactor this later
def sendFriendRequest(request):

    response = {"status":"failure", "message":"Internal failure"}

    if request.method == 'POST':

        jsonData = json.loads(request.body)

        # guid1 and author1 refer to the user initiating the friend request
        # guid2 and author2 refer to the user receiving the friend request
        guid1 = jsonData["author"]["id"]
        guid2 = jsonData["friend"]["author"]["id"]

        author1 = []
        author2 = []

        if jsonData["author"]["host"] == OURHOST:
            author1 = Author.objects.filter(guid=guid1)

        if jsonData["friend"]["author"]["host"] == OURHOST:
            author2 = Author.objects.filter(guid=guid2)

        # Both authors are local
        if len(author1) > 0 and len(author2) > 0:

            author1 = author1[0]
            author2 = author2[0]

            relationship = LocalRelationship.objects.filter(
                                ((Q(author1=author1) & Q(author2=author2))
                                |(Q(author2=author1) & Q(author1=author2))))

            if len(relationship) > 0:

                relationship = relationship[0]

                # author1 already follows or is friends with author2, no change
                if relationship.author1 == author1:
                    response["status"] = "success"
                    response["message"] = ("Already following %s, no change" %
                                            author2.user.username)
                # author2 follows author1, so now make them friends
                else:
                    relationship.relationship = True
                    relationship.save()
                    response["status"] = "success"
                    response["message"] = ("You are now friends with %s" %
                                            author2.user.username)
            else:
                # author1 will follow author2
                _, _ = LocalRelationship.objects.get_or_create(
                                                   author1=author1,
                                                   author2=author2,
                                                   relationship=False)
                response["status"] = "success"
                response["message"] = ("You are now following %s" %
                                            author2.user.username)

        # author1 is local, author2 is remote
        elif len(author1) > 0 and len(author2) == 0:

            author1 = author1[0]

            remoteAuthor, _ = RemoteAuthor.objects.get_or_create(guid=guid2)
            remoteAuthor.update(jsonData["friend"]["author"]["displayname"],
                                jsonData["friend"]["author"]["host"],
                                jsonData["friend"]["author"]["url"])

            relationship = RemoteRelationship.objects.filter(
                                localAuthor=author1, remoteAuthor=remoteAuthor)

            if len(relationship) > 0:

                relationship = relationship[0]

                # author1 already follows or is friends with author2, no change
                if relationship.relationship == (0 or 2):
                    response["status"] = "success"
                    response["message"] = ("Already following %s, no change" %
                                    jsonData["friend"]["author"]["displayname"])
                # author2 follows author1, so now make them friends
                else:
                    relationship.relationship = 2
                    relationship.save()
                    response["status"] = "success"
                    response["message"] = ("You are now friends with %s" %
                                    jsonData["friend"]["author"]["displayname"])
                    postFriendRequest(author1, remoteAuthor)
            else:
                # author1 will follow author2
                _, _ = RemoteRelationship.objects.get_or_create(
                                                   localAuthor=author1,
                                                   remoteAuthor=remoteAuthor,
                                                   relationship=0)
                response["status"] = "success"
                response["message"] = ("You are now following %s" %
                                    jsonData["friend"]["author"]["displayname"])
                postFriendRequest(author1, remoteAuthor)

        # author1 is remote, author2 is local
        elif len(author1) == 0 and len(author2) > 0:

            author2 = author2[0]

            remoteAuthor, _ = RemoteAuthor.objects.get_or_create(guid=guid1)
            remoteAuthor.update(jsonData["author"]["displayname"],
                                jsonData["author"]["host"],
                                jsonData["author"]["url"])

            relationship = RemoteRelationship.objects.filter(
                                localAuthor=author2, remoteAuthor=remoteAuthor)

            if len(relationship) > 0:

                relationship = relationship[0]

                # author1 already follows or is friends with author2, no change
                if relationship.relationship == (1 or 2):
                    response["status"] = "success"
                    response["message"] = ("Already following %s, no change" %
                                            author2.user.username)
                # author2 follows author1, so now make them friends
                else:
                    relationship.relationship = 2
                    relationship.save()
                    response["status"] = "success"
                    response["message"] = ("You are now friends with %s" %
                                            author2.user.username)
            else:
                # author1 will follow author2
                _, c = RemoteRelationship.objects.get_or_create(
                                                   localAuthor=author2,
                                                   remoteAuthor=remoteAuthor,
                                                   relationship=1)

                response["status"] = "success"
                response["message"] = ("You are now following %s" %
                                            author2.user.username)

        # either both authors are remote, or one of the users doesn't exist
        # we won't support either of these
        else:
            pass

    return HttpResponse(json.dumps(response),
                        content_type="application/json")


@api_view(['GET'])
def getPublicPosts(request):
    """
    Gets all public posts

    Fulfills from example-article.json
    http://service/posts (all posts marked as public on the server)
    """
    if request.method == 'GET':
        rawposts = Post.objects.filter(visibility=Post.PUBLIC)
        posts = buildFullPost(rawposts)
        return Response(serializeFullPost(posts))

@api_view(['GET','POST','PUT'])
def postSingle(request, post_id):
    """
    Retrieve a post, or update/create a post depending on request verb.

    Fulfills:
    Implement a restful API for http://service/post/{POST_ID}
        a PUT should insert/update a post
        a POST should get the post
        a GET should get the post
    """
    # Get the post
    if request.method == 'GET' or request.method == 'POST':
        try:
            rawpost = Post.objects.get(guid=post_id)
        except Post.DoesNotExist:
            return Response(status=404)

        # Extract the requesting author's information to check for visibility
        jsonData = json.loads(request.body)
        authorId = jsonData["author"]["id"]
        author = Author.objects.get(guid=authorId)

        if not rawpost.isAllowedToViewPost(author):
            return Response(status=403) 

        post = buildFullPost(rawpost)
        serializer = FullPostSerializer(post,many=True)
        return Response({"posts":serializer.data})

    # Update the post
    elif request.method == 'PUT':
        # for post in request.DATA:
        posts = Post.objects.filter(guid=post_id)
        newPost = None

        # post exists, so it will update
        if len(posts) > 0:
            # Only the author who made the post should be able to edit it
            if AuthorPost.objects.get(post=posts[0]).author.guid == author.guid:
                newPost = updatePost(posts[0], request.DATA)
            else:
                return Response(status=403) 
        else:    # post doesn't exist, a new one will be created
            newPost = createPost(request, request.DATA)
   
        # return new / updated post in body 
        serializer = FullPostSerializer(buildFullPost(newPost), many=True)
        print serializer.data
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def getAuthorPosts(request, requestedUserid):
    """
    Gets all the posts the requesting author can view of the requested author

    Fulfills:
    http://service/author/{AUTHOR_ID}/posts
    (all posts made by {AUTHOR_ID} visible to the currently authenticated user)
    """
    if request.user.is_authenticated():
        user = User.objects.get(username=request.user)
        viewingAuthor = Author.objects.get(user=user)

        try:
            requestedAuthor = Author.objects.get(guid=requestedUserid)
        except Author.DoesNotExist:
            return Response(status=404)

        if request.method == 'GET':
            rawposts = Post.getViewablePosts(viewingAuthor, requestedAuthor)
            posts = buildFullPost(rawposts)
            return Response(serializeFullPost(posts))

@api_view(['GET'])
def getStream(request):
    """
    Get's the currently authenicated author's stream. 

    Fulfills
        http://service/author/posts 
        (posts that are visible to the currently authenticated user)
    """
    if request.user.is_authenticated():
        user = User.objects.get(username=request.user)
        author = Author.objects.get(user=user)
        rawposts = Post.getAllowedPosts(author)

        if request.method == 'GET':
            posts = buildFullPost(rawposts)
            return Response(serializeFullPost(posts))
    else:
        return Response(status=403)

@api_view(['GET'])
def authorProfile(request, authorId):
    """
    Gets the author's information. Does not support updating your profile.
    
    Semi-fulfills:
    implement author profiles via http://service/author/userid
    """
    try:
        author = Author.objects.get(guid=authorId)
    except Author.DoesNotExist:
        return Response(status=404)

    # Get the author's information
    if request.method == 'GET':
        serializer = AuthorSerializer(author.as_dict())
        return Response(serializer.data)
