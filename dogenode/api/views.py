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

from author.models import Author, Relationship
from post.models import Post, AuthorPost, PostCategory
from comments.models import Comment
from categories.models import Category
from api.serializers import AuthorSerializer, FullPostSerializer

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
                response["friends"] = [int(userid1), int(userid2)]

    return HttpResponse(json.dumps(response),
                        content_type="application/json")

# The POST request is sent to a url which includes the user ID, but the user
# ID is also sent in the POST request body.
# Right now I am using the user ID sent in the request body
def getFriendsFromList(request, userid):

    # check if userid is actually an int first
    if userid.isdigit():

        response = {"query":"friends",
                    "author":int(userid),
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

    else:

        response = {"query":"friends",
                    "author":userid,
                    "friends":[]}


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


def buildFullPostContent(post):
    """
    Goes through all the fields of a Post 
    Should find a better way to go through all the fields of a post
    """
    # Post object
    postContent = {}
    postContent['guid'] = post.guid
    postContent['title'] = post.title
    postContent['description'] = post.description
    postContent['content'] = post.content
    postContent['visibility'] = post.visibility
    postContent['contentType'] = post.contentType
    postContent['origin'] = post.origin
    postContent['pubDate'] = post.pubDate
    postContent['modifiedDate'] = post.modifiedDate

    # other objects
    postContent["author"] = AuthorPost.objects.get(post=post).author
    postContent["comments"] = Comment.objects.filter(post_ref=post)

    categoryIds = PostCategory.objects.filter(post=post).values_list('category', flat=True)

    postContent["categories"] = Category.objects.filter(id__in=categoryIds)

    return postContent


def buildFullPost(rawposts):
    """
    From a list of just the posts, add in the author, comments, and 
    categories to the actual post information we are sending,
    as in example-article.json 
    """
    # If there is only one Post
    if type(rawposts) is Post:
        fullpost = buildFullPostContent(rawposts)

        return fullpost 
    else:
        posts = []

        for post in rawposts:
            fullpost = buildFullPostContent(post)

            posts.append(fullpost)            

        return posts

def serializeFullPost(posts):
    """
    Minor final Full Post cleanup to match example-article.json 
    """
    serializer = FullPostSerializer(posts, many=True)
    return {"posts":serializer.data}

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
def postSingle(request, pk):
    """
    Retrieve a post. Currently does not properly update/create a post.

    Semi-Fulfills:
    Implement a restful API for http://service/post/{POST_ID}
        a PUT should insert/update a post
        a POST should get the post
        a GET should get the post
    """
    try:
        rawpost = Post.objects.get(id=pk)
    except Post.DoesNotExist:
        return Response(status=404)

    # Check if the current author is allowed to view the post
    user = User.objects.get(username=request.user)
    author = Author.objects.get(user=user)

    if not rawpost.isAllowedToViewPost(author):
        return Response(status=403) 

    # Get the post
    if request.method == 'GET' or request.method == 'POST':
        post = buildFullPost(rawpost)
        serializer = FullPostSerializer(post)
        return Response({"posts":serializer.data})

    # Update the post
    elif request.method == 'PUT':
        post = buildFullPost(rawpost)
        serializer = FullPostSerializer(post, data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            return Response({"posts":serializer.data})
        return Response(serializer.errors, status=400)

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
            requestedAuthor = Author.objects.get(user=requestedUserid)
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
def authorProfile(request, userid):
    """
    Gets the author's information. Does not support updating your profile.
    
    Semi-fulfills:
    implement author profiles via http://service/author/userid
    """
    try:
        author = Author.objects.get(user=userid)
    except Author.DoesNotExist:
        return Response(status=404)

    # Get the author's information
    if request.method == 'GET':
        serializer = AuthorSerializer(author)
        return Response(serializer.data)

    # Update the author's information?
    #elif request.method == 'PUT':
    #    serializer = AuthorSerializer(author, data=request.DATA)
    #    if serializer.is_valid():
    #        serializer.save()
    #        return Response(serializer.data)
    #    return Response(serializer.errors, status=400)
