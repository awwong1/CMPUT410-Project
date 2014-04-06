from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from author.models import Author, RemoteAuthor, LocalRelationship, RemoteRelationship
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from post.views import createPost, updatePost, getJSONPost

from comments.models import Comment
from categories.models import Category
from api.utils import *

import sys
import datetime
import json
import requests
import urlparse

# List of other servers we are communicating with
SERVER_URLS = ['http://127.0.0.1:8001/', #BenHoboCo
               #'http://cs410.cs.ualberta.ca:41041/', #Team4, BenHoboCo
               #'http://cs410.cs.ualberta.ca:41051/', #Team5, PLKR
               ]

#TODO: not sure where best to put this POST request (authors/views uses it too)
def postFriendRequest(localAuthor, remoteAuthor):

    headers = {"Content-type": "application/json"}
    postData = {
                    "query":"friendrequest",
                    "author":{
                        "id":localAuthor.guid,
                        "host":settings.OUR_HOST,
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
            response = requests.post(
                        '%s/api/authors/%s/friends/' %
                                 (SERVER_URLS[0],
                                  remoteAuthor.displayName),
                         headers=headers,
                         data=json.dumps(postData))
            response.raise_for_status() # Exception on 4XX/5XX response

        except requests.exceptions.RequestException:
            #TODO: we should really let the user know the remote server
            # is down
            pass

# Searches local authors whose username contains the query string
#TODO: there's some repeated code here for searching authors in author/views
def search(request):

    query = request.GET.get("query", "")

    users = User.objects.filter(username__contains=query)

    authors = []

    # search locally
    for u in users:
        a = Author.objects.get(user=u)

        authors.append({"url": "%sauthor/profile/%s" % (settings.OUR_HOST,
                                                        a.guid),
                        "host": settings.OUR_HOST,
                        "displayname": a.user.username,
                        "id": a.guid})

    return HttpResponse(json.dumps(authors))

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

        if jsonData["author"]["host"] == settings.OUR_HOST:
            author1 = Author.objects.filter(guid=guid1)

        if jsonData["friend"]["author"]["host"] == settings.OUR_HOST:
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
        return HttpResponse(json.dumps({"posts": posts}), content_type="application/json")

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
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

        # Extract the requesting author's information to check for visibility
        host = request.META["REMOTE_ADDR"] + request.META["SERVER_NAME"]
        queryParams = urlparse.parse_qs(request.META["QUERY_STRING"])
        viewerId = queryParams["id"]
        viewable, post = getJSONPost(viewerId, post_id, host)

        if not viewable:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN) 

        post = buildFullPost(rawpost)
        return HttpResponse(json.dumps({"posts":post}), content_type="application/json")

    # Update the post
    elif request.method == 'PUT':
        # for post in request.DATA:
        posts = Post.objects.filter(guid=post_id)
        newPost = None
        queryParams = urlparse.parse_qs(request.META["QUERY_STRING"])
        authorId = queryParams["id"][0]
        try:
            author = Author.objects.get(guid=authorId)
        except Author.DoesNotExist:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        # post exists, so it will update
        if len(posts) > 0:
            # Only the author who made the post should be able to edit it
            if AuthorPost.objects.get(post=posts[0]).author.guid == author.guid:
                newPost = updatePost(posts[0], request.DATA)
            else:
                return HttpResponse(status=status.HTTP_403_FORBIDDEN) 
        else:    # post doesn't exist, a new one will be created
            newPost = createPost(request, post_id, request.DATA)
   
        # return new / updated post in body 
        jsonPost = json.dumps(buildFullPost(newPost))
        return HttpResponse(jsonPost, status=status.HTTP_201_CREATED,
                            content_type="application/json")

@api_view(['GET', 'POST'])
def getAuthorPosts(request, requestedAuthorId):
    """
    Gets all the posts the requesting author can view of the requested author

    Fulfills:
    http://service/author/{AUTHOR_ID}/posts?id={VIEWING_AUTHOR_ID}
    (all posts made by {AUTHOR_ID} visible to the currently authenticated user)
    """
    if request.method == 'GET' or request.method == 'POST':
        # Extract the requesting author's information to check for visibility
        host = request.META["REMOTE_ADDR"] + request.META["SERVER_NAME"]
        queryParams = urlparse.parse_qs(request.META["QUERY_STRING"])
        viewerId = queryParams["id"]
       
        try: 
            requestedAuthor = Author.objects.get(guid=requestedAuthorId)
        except Author.DoesNotExist:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

        postIds = AuthorPost.objects.filter(author=requestedAuthor).values_list(
                            'post', flat=True)
        postsByAuthor = Post.objects.filter(id__in=postIds).order_by(
                            '-pubDate')
        rawPosts = []
        for post in postsByAuthor:

            viewable, rawPost = getJSONPost(viewerId, post.guid, host)
            if viewable:
                rawPosts.append(rawPost)

        finalPosts = buildFullPost(rawPosts)
        return HttpResponse(json.dumps({"posts":finalPosts}), 
                            content_type="application/json")

@api_view(['GET', 'POST'])
def getStream(request):
    """
    Get's the currently authenicated author's stream. 

    Fulfills
        http://service/author/posts?id={viewingAuthorId} 
        (posts that are visible to the currently authenticated user)
    """
    if request.method == 'GET' or request.method == 'POST':
        # Extract the requesting author's information to check for visibility
        host = request.META["REMOTE_ADDR"] + request.META["SERVER_NAME"]
        queryParams = urlparse.parse_qs(request.META["QUERY_STRING"])
        viewerId = queryParams["id"]
 
        allPosts = Post.objects.all().order_by('-pubDate')
        rawPosts = []
        for post in allPosts:

            viewable, rawPost = getJSONPost(viewerId, post.guid, host, True)

            if viewable:
                rawPosts.append(rawPost)

        finalPosts = buildFullPost(rawPosts)
        return HttpResponse(json.dumps({"posts":finalPosts}), 
                            content_type="application/json")

    else:
        HttpResponse(status=status.status.HTTP_METHOD_NOT_ALLOWED)

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
        return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    # Get the author's information
    if request.method == 'GET':
        return HttpResponse(json.dumps(author.as_dict()))
