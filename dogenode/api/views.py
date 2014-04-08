from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.models import AllowedServer
from api.utils import *
from author.models import Author, RemoteAuthor, LocalRelationship, RemoteRelationship
from categories.models import Category
from comments.models import Comment
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory

import base64
import datetime
import json
import requests
import sys
import urlparse

#TODO: not sure where best to put this POST request (authors/views uses it too)
def postFriendRequest(localAuthor, remoteAuthor, befriend=True):

    headers = {"Content-type": "application/json"}
    postData = {
                    "query": "friendrequest" if befriend else "unfriend",
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
    servers = AllowedServer.objects.all()

    for server in servers:

        if remoteAuthor.host == server.host:
            try:
                response = requests.post(
                            '%sfriendrequest' % server.host,
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
@csrf_exempt
def sendFriendRequest(request):

    response = {"status":"failure", "message":"Internal failure"}
    status = 500

    if request.method == 'POST':

        jsonData = json.loads(request.body)

        # guid1 and author1 refer to the user initiating the friend request
        # guid2 and author2 refer to the user receiving the friend request
        guid1 = jsonData["author"]["id"]
        guid2 = jsonData["friend"]["author"]["id"]

        author1 = Author.objects.filter(guid=guid1)
        author2 = Author.objects.filter(guid=guid2)

        if jsonData["query"] == "unfriend":
            # Both authors are local
            if len(author1) > 0 and len(author2) > 0:

                author1 = author1[0]
                author2 = author2[0]

                relationship = LocalRelationship.objects.filter(
                                    ((Q(author1=author1) & Q(author2=author2))
                                    |(Q(author2=author1) & Q(author1=author2))))

                if len(relationship) > 0:

                    relationship = relationship[0]

                    # they are friends
                    if relationship.relationship:
                        relationship.delete()

                        # author2 still follows author1
                        LocalRelationship.objects.get_or_create(
                                                    author1=author2,
                                                    author2=author1,
                                                    relationship=False)

                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You are no longer friends"
                                               " with %s"
                                               % author2.user.username)

                    else:
                        # author1 follows author2
                        if relationship.author1 == author1:
                            relationship.delete()
                            status = 200
                            response["status"] = "success"
                            response["message"] = ("You are no longer"
                                                   " following %s"
                                                   % author2.user.username)
                        # author2 follows author1
                        else:
                            status = 200
                            response["status"] = "success"
                            response["message"] = ("You already have no"
                                                   " relationship with %s,"
                                                   " no change" %
                                                    author2.user.username)

                else:
                    # author1 already has no relationship with author2
                    status = 200
                    response["status"] = "success"
                    response["message"] = ("You already have no relationship"
                                           " with %s, no change" %
                                            author2.user.username)

            # author1 is local, author2 is remote
            elif len(author1) > 0 and len(author2) == 0:

                author1 = author1[0]

                remoteAuthor, _ = RemoteAuthor.objects.get_or_create(guid=guid2)
                remoteAuthor.update(jsonData["friend"]["author"]["displayname"],
                                    jsonData["friend"]["author"]["host"],
                                    jsonData["friend"]["author"]["url"])

                relationship = RemoteRelationship.objects.filter(
                                    localAuthor=author1,
                                    remoteAuthor=remoteAuthor)

                if len(relationship) > 0:

                    relationship = relationship[0]

                    # they are friends
                    if relationship.relationship == 2:
                        relationship.relationship = 1
                        relationship.save()
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You are no longer friends"
                                               " with %s" %
                                    jsonData["friend"]["author"]["displayname"])
                        postFriendRequest(author1, remoteAuthor, False)
                    # author1 follows author2
                    elif relationship.relationship == 0:
                        relationship.delete()
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You are no longer"
                                               " following %s" %
                                    jsonData["friend"]["author"]["displayname"])
                        postFriendRequest(author1, remoteAuthor, False)
                    # author1 already has no relationship with author2
                    else:
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You already have no"
                                               " relationship  with %s,"
                                               " no change" %
                                    jsonData["friend"]["author"]["displayname"])
                else:
                    # author1 already has no relationship with author2
                    status = 200
                    response["status"] = "success"
                    response["message"] = ("You already have no relationship"
                                           " with %s, no change" %
                                    jsonData["friend"]["author"]["displayname"])

            # author1 is remote, author2 is local
            elif len(author1) == 0 and len(author2) > 0:

                author2 = author2[0]

                remoteAuthor, _ = RemoteAuthor.objects.get_or_create(guid=guid1)
                remoteAuthor.update(jsonData["author"]["displayname"],
                                    jsonData["author"]["host"])

                relationship = RemoteRelationship.objects.filter(
                                localAuthor=author2, remoteAuthor=remoteAuthor)

                if len(relationship) > 0:

                    relationship = relationship[0]

                    # they are friends
                    if relationship.relationship == 2:
                        relationship.relationship = 0
                        relationship.save()
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You are no longer friends"
                                               " with %s" %
                                                author2.user.username)
                    # author1 follows author2
                    elif relationship.relationship == 1:
                        relationship.delete()
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You are no longer"
                                               " following %s" %
                                                author2.user.username)
                    # author1 already has no relationship with author2
                    else:
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You already have no"
                                               " relationship  with %s,"
                                               " no change" %
                                                author2.user.username)
                else:
                    # author1 already has no relationship with author2
                    status = 200
                    response["status"] = "success"
                    response["message"] = ("You already have no relationship"
                                           " with %s, no change" %
                                            author2.user.username)

            # either both authors are remote, or one of the users doesn't exist
            # we won't support either of these
            else:
                pass

        else:
            # Both authors are local
            if len(author1) > 0 and len(author2) > 0:

                author1 = author1[0]
                author2 = author2[0]

                relationship = LocalRelationship.objects.filter(
                                    ((Q(author1=author1) & Q(author2=author2))
                                    |(Q(author2=author1) & Q(author1=author2))))

                if len(relationship) > 0:

                    relationship = relationship[0]

                    # author1 already follows or is friends with author2
                    if relationship.author1 == author1:
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("Already following %s,"
                                               "no change" %
                                                author2.user.username)
                    # author2 follows author1, so now make them friends
                    else:
                        relationship.relationship = True
                        relationship.save()
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You are now friends with %s" %
                                                author2.user.username)

                else:
                    # author1 will follow author2
                    _, _ = LocalRelationship.objects.get_or_create(
                                                       author1=author1,
                                                       author2=author2,
                                                       relationship=False)
                    status = 200
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
                                    localAuthor=author1,
                                    remoteAuthor=remoteAuthor)

                if len(relationship) > 0:

                    relationship = relationship[0]

                    # author1 already follows or is friends with author2
                    if relationship.relationship == (0 or 2):
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("Already following %s,"
                                               "no change" %
                                    jsonData["friend"]["author"]["displayname"])
                    # author2 follows author1, so now make them friends
                    else:
                        relationship.relationship = 2
                        relationship.save()
                        status = 200
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
                    status = 200
                    response["status"] = "success"
                    response["message"] = ("You are now following %s" %
                                    jsonData["friend"]["author"]["displayname"])
                    postFriendRequest(author1, remoteAuthor)

            # author1 is remote, author2 is local
            elif len(author1) == 0 and len(author2) > 0:

                author2 = author2[0]

                remoteAuthor, _ = RemoteAuthor.objects.get_or_create(guid=guid1)
                remoteAuthor.update(jsonData["author"]["displayname"],
                                    jsonData["author"]["host"])

                relationship = RemoteRelationship.objects.filter(
                                localAuthor=author2, remoteAuthor=remoteAuthor)

                if len(relationship) > 0:

                    relationship = relationship[0]

                    # author1 already follows or is friends with author2
                    if relationship.relationship == (1 or 2):
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("Already following %s"
                                               ", no change" %
                                                author2.user.username)
                    # author2 follows author1, so now make them friends
                    else:
                        relationship.relationship = 2
                        relationship.save()
                        status = 200
                        response["status"] = "success"
                        response["message"] = ("You are now friends with %s" %
                                                author2.user.username)
                else:
                    # author1 will follow author2
                    _, c = RemoteRelationship.objects.get_or_create(
                                                   localAuthor=author2,
                                                   remoteAuthor=remoteAuthor,
                                                   relationship=1)

                    status = 200
                    response["status"] = "success"
                    response["message"] = ("You are now following %s" %
                                                author2.user.username)

            # either both authors are remote, or one of the users doesn't exist
            # we won't support either of these
            else:
                pass

    return HttpResponse(json.dumps(response), status=status,
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
        viewable, post = __getJSONPost(viewerId, post_id, host)

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
                newPost = __updatePost(posts[0], request.DATA)
            else:
                return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        else:    # post doesn't exist, a new one will be created
            newPost = __createPost(request, post_id, request.DATA)

        # return new / updated post in body
        jsonPost = json.dumps(buildFullPost(newPost))
        return HttpResponse(jsonPost, status=status.HTTP_201_CREATED,
                            content_type="application/json")

@api_view(['GET', 'POST'])
def getAuthorPostsAsJSON(request, requestedAuthorId):
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

        viewerId = None
        try:
            viewerId = queryParams["id"]
        except KeyError:
            viewerId = [Author.objects.get(user=request.user).guid]

        if not viewerId:
            return HttpResponse(json.dumps([]),
                                content_type="application/json",
                                status_code=400)

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

            viewable, rawPost = __getJSONPost(viewerId, post.guid, host)
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
        viewerId = None

        try:
            viewerId = queryParams["id"]
        except KeyError:
            viewerId = [Author.objects.get(user=request.user).guid]

        if not viewerId:
            return HttpResponse(json.dumps([]),
                                content_type="application/json",
                                status_code=400)

        allPosts = Post.objects.all().order_by('-pubDate')
        rawPosts = []

        for post in allPosts:

            viewable, rawPost = __getJSONPost(viewerId, post.guid, host, check_follow=True)

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

def __createPost(request, post_id, data):
    """
    Creates a new post from json representation of a post.
    """
    guid = post_id
    title = data.get("title")
    description = data.get("description", "")
    content = data.get("content")
    visibility = data.get("visibility", Post.PRIVATE)
    visibilityExceptionsString = data.get("visibilityExceptions", "")
    categoriesString = data.get("categories", "")
    contentType = data.get("content-type", Post.PLAIN)
    imageIdsString = data.get("image-ids", "")

    categoryNames = categoriesString.split()
    exceptionUsernames = visibilityExceptionsString.split()
    imageIds = imageIdsString.split()
    author = Author.objects.get(user=request.user)
    newPost = Post.objects.create(guid=guid, title=title,
                                  description=description,
                                  content=content, visibility=visibility,
                                  contentType=contentType)
    newPost.origin = request.build_absolute_uri(newPost.get_absolute_url())
    newPost.save()

    # If there are also images, handle that too
    images = Image.objects.filter(id__in=imageIds)
    for i in images:
        i.visibility = visibility # image adopts visibility of post
        i.save()
        ImagePost.objects.get_or_create(image=i, post=newPost)

    AuthorPost.objects.create(post=newPost, author=author)

   # I use (abuse) get_or_create to curtail creating duplicates
    for name in categoryNames:
        categoryObject, _ = Category.objects.get_or_create(name=name)
        PostCategory.objects.get_or_create(post=newPost,
                                           category=categoryObject)
    for name in exceptionUsernames:
        try:
            userObject = User.objects.get(username=name)
            authorObject = Author.objects.get(user=userObject)
            PostVisibilityException.objects.get_or_create(post=newPost,
                author=authorObject)
            for i in images:
                ImageVisibilityException.objects.get_or_create(
                        image=i, author=authorObject)
        except ObjectDoesNotExist:
            pass

    return newPost

def __updatePost(post, data):
    """
    Completely updates or partially updates a post given post data in
    json format.
    """
    for key, value in data.items():
        setattr(post, key, value)
    post.modifiedDate = datetime.datetime.now()
    post.save()
    return post

def __getJSONPost(viewer_id, post_id, host, check_follow=False):
    """
    Returns a post. The currently authenticated
    user must also have permissions to view the post, else it will not be
    shown.

    Return value will be a tuple. The first element will be a boolean,
    True if the viewer is allowed to see the post, and False if they
    are not allowed.

    The second element will be the post retrieved. If no post matching
    the post id given was found, it will be None.
    """
    try:
        post = Post.objects.get(guid=post_id)
    except Post.DoesNotExist:
        return (False, None)

    postAuthor = AuthorPost.objects.get(post=post).author
    components = getPostComponents(post)
    viewerGuid = viewer_id[0]

    # dealing with local authors
    if len(Author.objects.filter(guid=viewerGuid)) > 0:
        return (post.isAllowedToViewPost(
                    Author.objects.get(guid=viewerGuid), check_follow),
                post)

    # dealing with remote authors
    viewers = RemoteAuthor.objects.filter(guid=viewerGuid)
    if (len(viewers) > 0):
        viewer = viewers[0]
    else:
        viewer = RemoteAuthor.objects.create(guid=viewerGuid, host=host)

    viewable = False
    authorFriends = postAuthor.getFriends()
    authorFollowedBy = postAuthor.getPendingReceivedRequests()

    # Only want to get public posts of people you follow or are friends with
    if post.visibility == Post.PUBLIC:
        if not check_follow:
            return (True, post)
        elif (viewer in authorFriends["remote"] or
              viewer in authorFollowedBy["remote"]):
            return (True, post)
        else:
            return (False, post)

    elif post.visibility == Post.SERVERONLY:
        viewable = False
    elif post.visibility == Post.FRIENDS or post.visibility == Post.FOAF:
        if viewer in authorFriends["remote"]:
            viewable = True
    elif post.visibility == Post.FOAF:
        allFriends = authorFriends["remote"] + authorFriends["local"]
        for friend in authorFriends["local"]:
            # TODO: fix for remote cases
            try:
                response = requests.get("%sapi/friends/%s/%s" %
                                            (settings.OUR_HOST,
                                            str(viewerGuid),
                                            str(postAuthor.guid)))
            except:
                viewable = False
                break

            if response.json()["friends"] != "NO":
                viewable = True
                break

    elif post.visibility == Post.PRIVATE:
        if viewerGuid == postAuthor.guid:
            viewable = True

    return (viewable, post)

def rawPostViewConverter(rawpost):
    """
    Attempt to kludge a raw post into a django template post viewable
    else return None
    """
    postData = {'external':True}
    authData = {}
    commentsData = []
    categoriesData = {}
    visibilityExceptionsData = {}
    imagesData = {}
    unifiedpost = {}

    try:
        postData['HTML']="text/html"
        postData['MARKDOWN']="text/x-markdown"
        postData['PLAIN']="text/plain"
        postData['guid']=rawpost['guid']
        postData['title']=rawpost['title']
        postData['description']=rawpost['description']
        postData['content']=rawpost['content']
        postData['visibility']=rawpost['visibility']
        try:
            postData['contentType']=rawpost['content-type']
        except:
            pass
        try:
            postData['contentType']=rawpost['contentType']
        except:
            pass
        postData['origin']=rawpost['origin']
        postData['source']=rawpost['source']
        postData['pubDate']=rawpost['pubDate']


        authData['displayname']=rawpost['author']['displayname']
        authData['url']=rawpost['author']['url']
        authData['host']=rawpost['author']['host']
        authData['guid']=rawpost['author']['id']

        for rawComment in rawpost['comments']:
            rawauth = {}
            rawauth['displayname'] = rawComment['author']['displayname']
            # Note: author url isn't actually part of spec in samplejson
            try:
                rawauth['url'] = rawComment['author']['url']
            except:
                rawauth['url'] = '/'
            rawauth['host'] = rawComment['author']['host']
            rawauth['guid'] = rawComment['author']['id']

            # attach with rest of the comment
            adaptcomment = {}
            adaptcomment['author']=rawauth
            adaptcomment['comment']=rawComment['comment']
            adaptcomment['guid']=rawComment['guid']


            # this is to get it working with group 6 sempais
            try:
                adaptcomment['pubDate']=rawComment['pubDate']
            except:
                pass
            try:
                adaptcomment['pubDate']=rawComment['PubDate']
            except:
                pass
            commentsData.append(adaptcomment)

        unifiedpost = (postData, authData, commentsData, categoriesData,
                   visibilityExceptionsData, imagesData)

    except Exception as e:
        print ("doge: failed to parse post,\n{0}".format(e))
        unifiedpost = None
        print("Something didn't parse properly at all!\n\n")

    return unifiedpost
