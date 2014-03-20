from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from author.models import Author, Relationship
from post.models import Post
from api.serializers import PostSerializer, AuthorSerializer

import json

def areFriends(request, userid1, userid2):

    response = {"query":"friends",
                "friends":"NO"}

    if request.method == 'POST':

        user1 = User.objects.filter(id=userid1)
        user2 = User.objects.filter(id=userid2)

        if len(user1) > 0 and len(user2) > 0:

            author1, _ = Author.objects.get_or_create(user=user1[0])
            author2, _ = Author.objects.get_or_create(user=user2[0])

            if author2 in author1.getFriends():
                response["friends"] = [userid1, userid2]

    return HttpResponse(json.dumps(response),
                        content_type="application/json")

# The POST request is sent to a url which includes the user ID, but the user
# ID is also sent in the POST request body.
# Right now I am using the user ID sent in the request body
def getFriendsFromList(request, userid):

    response = {"query":"friends",
                "author":userid,
                "friends":[]}

    if request.method == 'POST':

        jsonData = json.loads(request.body)

        userid = jsonData['author']
        user = User.objects.filter(id=userid)

        if len(user) > 0:

            author, _ = Author.objects.get_or_create(user=user)

            friendUserids = [a.user.id for a in author.getFriends()]
            
            friends = list(set(friendUserids) & set(jsonData["authors"]))
            
            response["author"] = userid
            response["friends"] = friends

    return HttpResponse(json.dumps(response),
                        content_type="application/json")

def sendFriendRequest(request):

    response = {"status":"failure", "message":"Internal failure"}

    if request.method == 'POST':

        jsonData = json.loads(request.body)

        userid1 = jsonData["author"]["id"]
        userid2 = jsonData["friend"]["author"]["id"]

        user1 = User.objects.filter(id=userid1)
        user2 = User.objects.filter(id=userid2)

        if len(user1) > 0 and len(user2) > 0:

            user1 = user1[0]
            user2 = user2[0]

            author1, _ = Author.objects.get_or_create(user=user1)
            author2, _ = Author.objects.get_or_create(user=user2)
            
            relationship = Relationship.objects.filter(
                                ((Q(author1=author1) & Q(author2=author2))
                                |(Q(author2=author1) & Q(author1=author2))))

            if len(relationship) > 0:

                relationship = relationship[0]

                # author1 already follows author2, no change
                if relationship.author1 == author1:
                    response["status"] = "success"
                    response["message"] = ("Already following %s, no change" %
                                            user2.username)
                # author2 follows author1, so now make them friends
                else:
                    relationship.relationship = True
                    relationship.save()
                    response["status"] = "success"
                    response["message"] = ("You are now friends with %s" %
                                            user2.username)
            else:
                # author1 will follow author2
                _, _ = Relationship.objects.get_or_create(
                                                   author1=author1,
                                                   author2=author2,
                                                   relationship=False)
                response["status"] = "success"
                response["message"] = ("You are now following %s" %
                                            user2.username)

    return HttpResponse(json.dumps(response),
                        content_type="application/json")


@api_view(['GET'])
def postsPublic(request):
    """
    List all public posts
    """
    if request.method == 'GET':
        posts = Post.objects.filter(visibility=Post.PUBLIC)
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

@api_view(['GET','PUT','DELETE'])
def postSingle(request, pk):
    """
    Retrieve, update or delete a post.
    """
    try:
        post = Post.objects.get(id=pk)
    except Post.DoesNotExist:
        return Response(status=404)

    # Check if the current author is allowed to view the post
    user = User.objects.get(username=request.user)
    author = Author.objects.get(user=user)

    if not post.isAllowedToViewPost(author):
        return Response(status=403) 

    # Get the post
    if request.method == 'GET':
        serializer = PostSerializer(post)
        return Response(serializer.data)

    # Update the post
    elif request.method == 'PUT':
        serializer = PostSerializer(post, data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    # Delete the post
    elif request.method == 'DELETE':
        post.delete()
        return Response(status=204) 

@api_view(['GET'])
def getAuthorPosts(request, requestedUsername):
    """
    Gets all the posts the requesting author can view of the requested author
    """

    if request.user.is_authenticated():
        user = User.objects.get(username=request.user)
        viewingAuthor = Author.objects.get(user=user)

        try:
            requestedUser = User.objects.get(username=requestedUsername)
            requestedAuthor = Author.objects.get(user=requestedUser)
        except Author.DoesNotExist:
            return Response(status=404)

        if request.method == 'GET':
            posts = Post.getViewablePosts(viewingAuthor, requestedAuthor)
            serializer = PostSerializer(posts)
            return Response(serializer.data)

@api_view(['GET'])
def getStream(request):
    """
    Implementing:
        http://service/author/posts 
        (posts that are visible to the currently authenticated user)
    """
    if request.user.is_authenticated():
        user = User.objects.get(username=request.user)
        author = Author.objects.get(user=user)
        posts = Post.getAllowedPosts(author)

        if request.method == 'GET':
            serializer = PostSerializer(posts)
            return Response(serializer.data)
    else:
        return Response(status=403)

@api_view(['GET','PUT'])
def authorProfile(request, username):
    """
    Gets or updates the author's information
    """
    try:
        user = User.objects.get(username=username)
        author = Author.objects.get(user=user)
    except Author.DoesNotExist:
        return Response(status=404)

    # Get the author's information
    if request.method == 'GET':
        serializer = AuthorSerializer(author)
        return Response(serializer.data)

    # Update the author's information
    elif request.method == 'PUT':
        serializer = PostSerializer(author, data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
