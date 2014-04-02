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
from comments.models import Comment
from categories.models import Category
from api.serializers import AuthorSerializer, FullPostSerializer

import sys
import datetime
import json

#TODO: find a way to get this value automatically
OURHOST = "http://127.0.0.1:8000/"

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

            relationship = RemoteRelationship.objects.filter(
                                localAuthor=author1, remoteAuthor=guid2)

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
            else:
                # author1 will follow author2
                _, _ = RemoteRelationship.objects.get_or_create(
                                                   localAuthor=author1,
                                                   remoteAuthor=guid2,
                                                   relationship=0)
                response["status"] = "success"
                response["message"] = ("You are now following %s" %
                                    jsonData["friend"]["author"]["displayname"])

        # author1 is remote, author2 is local
        elif len(author1) == 0 and len(author2) > 0:

            author2 = author2[0]

            relationship = RemoteRelationship.objects.filter(
                                localAuthor=author2, remoteAuthor=guid1)

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
                _, _ = RemoteRelationship.objects.get_or_create(
                                                   localAuthor=author2,
                                                   remoteAuthor=guid1,
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


def buildFullPostContent(post):
    """
    Goes through all the fields of a Post 
    Should find a better way to go through all the fields of a post
    """
    # Post object
    postContent = buildPost(post)

    # other objects
    author = AuthorPost.objects.get(post=post).author
    postContent["author"] = buildAuthor(author)
    postContent["comments"] = buildComment(post)

    categoryIds = PostCategory.objects.filter(post=post).values_list(
        'category', flat=True)

    postContent["categories"] = Category.objects.filter(id__in=categoryIds)

    # Get Author visibility exceptions
    otherAuthorIds = PostVisibilityException.objects.filter(
                        post=post).values_list('author', flat=True)

    othAuthors = Author.objects.filter(id__in=otherAuthorIds)
    otherAuthors = [buildAuthor(auth) for auth in othAuthors]
    postContent["visibilityExceptions"] = otherAuthors

    return postContent

def buildPost(post):
    return {'guid' : post.guid,
             'title' : post.title,
             'description' : post.description,
             'content' : post.content,
             'visibility': post.visibility,
             'contentType' : post.contentType,
             'origin' : post.origin,
             'pubDate' : post.pubDate,
             'modifiedDate' : post.modifiedDate }

def buildAuthor(author):
    return {"id": author.guid,
            "displayName": author.user.username,
            "host": author.host,
            "url": author.url }

def buildComment(post):
    comments = Comment.objects.filter(post_ref=post)
    commentContent = []
    for comment in comments:
        currentComment = {}
        currentComment = {"guid": comment.guid,
                           "author": buildAuthor(comment.author),
                           "comment": comment.comment,
                           "pub_date": comment.pub_date
                          }
        commentContent.append(currentComment)

    return commentContent

def buildFullPost(rawposts):
    """
    From a list of just the posts, add in the author, comments, and 
    categories to the actual post information we are sending,
    as in example-article.json 
    """
    # If there is only one Post
    if type(rawposts) is Post:
        post= []
        fullpost = buildFullPostContent(rawposts)
        post.append(fullpost)
        return post 
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
        print(posts)

        return Response(serializeFullPost(posts))

@api_view(['GET','POST','PUT'])
def postSingle(request, post_id):
    """
    Retrieve a post. Currently does not properly update/create a post.

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
        data = request.DATA
        posts = Post.objects.filter(guid=post_id)
        user = User.objects.get(username=request.user)
        author = Author.objects.get(user=user)

        # post exists, so it will update
        if len(posts) > 0:
            # Only the author who made the post should be able to edit it
            if AuthorPost.objects.get(post=posts[0]).author.guid == author.guid:
                for key, value in data.items():
                    setattr(posts[0], key, value)
                posts[0].modifiedDate = datetime.datetime.now()
                posts[0].save()
            else:
                return Response(status=403) 
        else:    # post doesn't exist, a new one will be created
            post = Post.objects.create(**data)
            post.guid = post_id
            post.origin = request.build_absolute_uri(post.get_absolute_url())
            post.save()
            AuthorPost.objects.create(post=post, author=author)
    
        return Response(status=status.HTTP_201_CREATED)

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

    authorInfo = buildAuthor(author)

    # Get the author's information
    if request.method == 'GET':
        serializer = AuthorSerializer(authorInfo)
        return Response(serializer.data)

