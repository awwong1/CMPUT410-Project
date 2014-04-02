from django.shortcuts import (get_object_or_404, render, redirect,
                              render_to_response)
from django.http import HttpResponse
from django.template import RequestContext
from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from author.models import (Author, RemoteAuthor,
                           LocalRelationship, RemoteRelationship)
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from categories.models import Category
from comments.models import Comment
from images.models import Image, ImagePost, ImageVisibilityException

import markdown, json
import uuid
import urllib2

# List of other servers we are communicating with
SERVER_URLS = ['http://127.0.0.1:8001' #BenHoboCo
              ]

def isUserAccepted(user):
    author = Author.objects.filter(user=user)
    if len(author) > 0:
        return author[0].accepted

    return False

@ensure_csrf_cookie
def index(request):
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        #https://docs.djangoproject.com/en/dev/topics/auth/default/#authenticating-users
        user = authenticate(username=username, password=password)

        if user:
            # the password verified for the user and the user is accepted
            if isUserAccepted(user):
                login(request, user)
                return redirect('/author/stream/')
            else:
                context['message'] = ("Server admin has not accepted your "
                                      "registration yet!")
                return render(request, 'login/index.html', context)
        else:
            # Incorrect username and password
            context['message'] = "Incorrect username and password."
            return render(request, 'login/index.html', context)

    return render(request, 'login/index.html', context)

@ensure_csrf_cookie
def logUserOut(request):
    context = RequestContext(request)
    if request.method == "POST":
        logout(request)
    return redirect("/")

@ensure_csrf_cookie
def register(request):
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password1']

        # Check if username already exists
        if len(User.objects.filter(username=username)) > 0:
            context = RequestContext(request, {'registrationStatus':
                "The username '%s' is taken!" % username})
        else:
            if username and password:
                user = User.objects.create_user(username=username,
                                                password=password)
                user.save()
                return redirect('/login/')

    return render(request, 'login/register.html', context)

def profile(request, author_id):
    """
    GET: Returns the profile page / information of an author.
    """
    if request.user.is_authenticated():
        #user = User.objects.get(id=user_id)
        author = Author.objects.get(guid=author_id)
        viewer = Author.objects.get(user=request.user)
        user = author.user
        payload = { } # This is what we send in the RequestContext

        payload['author_id'] = viewer.guid
        payload['firstName'] = user.first_name or ""
        payload['lastName'] = user.last_name or ""
        payload['username'] = user.username
        payload['host'] = author.host or ""
        payload['url'] = author.url or request.build_absolute_uri(author.get_absolute_url())
        payload['userIsAuthor'] = (user.username == request.user.username)
        context = RequestContext(request, payload)
        viewer = Author.objects.get(user=User.objects.get(
                username=request.user))
        context['authPosts'] = Post.getViewablePosts(viewer, author)
        return render(request, 'author/profile.html', context)
    else:
        return redirect('/login/')

def editProfile(request):
    """
    Renders html page to allow for editing of profile in web browser.
    GET: Renders the page, populating the necessary fields.
    POST: Updates an author's information.
    """
    if request.user.is_authenticated():
        user = request.user
        author = Author.objects.get(user=request.user)
        payload = { } # This is what we send in the RequestContext

        if request.method == 'POST':

            newFirstName = request.POST['firstName']
            newLastName = request.POST['lastName']
            oldPassword = request.POST['oldPassword']
            newPassword = request.POST['newPassword']

            user.first_name = newFirstName or user.first_name
            user.last_name = newLastName or user.last_name
            user.save()

            payload['successMessage'] = "Profile updated."

            if newPassword:
                if user.check_password(oldPassword):
                    user.set_password(newPassword)
                    user.save()
                else:
                    payload['failureMessage'] = "Old password incorrect."

        payload['firstName'] = user.first_name or ""
        payload['lastName'] = user.last_name or ""
        payload['username'] = user.username
        payload['author_id'] = author.guid

        context = RequestContext(request, payload)
        return render(request, 'author/edit_profile.html', context)
    else:
        return redirect('/login/')

def getAuthorPosts(request, author_id):
    """
    Retrieves all posts made by the author specified and that are visible
    to currently authenticated user

    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
       return render(request, 'login/index.html', context)

    viewer = Author.objects.get(user=request.user)
    author = Author.objects.get(guid=author_id)

    postIds = AuthorPost.objects.filter(author=author).values_list(
                'post', flat=True)

    posts = Post.getViewablePosts(viewer, author)
    comments = []
    categories = []
    visibilityExceptions = []
    images = []

    for post in posts:
        categoryIds = PostCategory.objects.filter(post = post).values_list(
                        'category', flat=True)
        authorIds = PostVisibilityException.objects.filter(
                        post=post).values_list('author', flat=True)
        imageIds = ImagePost.objects.filter(post=post).values_list(
                        'image', flat=True)

        comments.append(Comment.objects.filter(post_ref=post))
        categories.append(Category.objects.filter(id__in=categoryIds))
        visibilityExceptions.append(Author.objects.filter(
                                        id__in=authorIds))
        images.append(Image.objects.filter(id__in=imageIds))

        # Convert Markdown into HTML for web browser 
        # django.contrib.markup is deprecated in 1.6, so, workaround
        if post.contentType == post.MARKDOWN:
            post.content = markdown.markdown(post.content)

    context["posts"] = zip(posts, comments, categories, visibilityExceptions,
                           images)
    context["author_id"] = author.guid

    return render_to_response('post/posts.html', context)


def stream(request):
    """
    Returns the stream of an author (all posts author can view)
    If calling the function restfully, call by sending a GET request to /author/posts 
    """
    if request.user.is_authenticated():
        context = RequestContext(request)
        author = Author.objects.get(user=request.user)
        rawposts = Post.getAllowedPosts(author)
        comments = []
        authors = []
        categories = []
        visibilityExceptions = []
        images = []

        for post in rawposts:
            categoryIds = PostCategory.objects.filter(post=post).values_list(
                            'category', flat=True)
            authorIds = PostVisibilityException.objects.filter(
                            post=post).values_list('author', flat=True)
            imageIds = ImagePost.objects.filter(post=post).values_list(
                            'image', flat=True)

            authors.append(AuthorPost.objects.get(post=post).author)
            comments.append(Comment.objects.filter(post_ref=post))
            categories.append(Category.objects.filter(id__in=categoryIds))
            visibilityExceptions.append(Author.objects.filter(
                id__in=authorIds))
            images.append(Image.objects.filter(id__in=imageIds))

            # Convert Markdown into HTML for web browser 
            # django.contrib.markup is deprecated in 1.6, so, workaround
            if post.contentType == post.MARKDOWN:
                post.content = markdown.markdown(post.content)

        # Stream payload
        context['posts'] = zip(rawposts, authors, comments, categories, 
                               visibilityExceptions, images)
        # Make a Post payload
        context['visibilities'] = Post.VISIBILITY_CHOICES
        context['contentTypes'] = Post.CONTENT_TYPE_CHOICES
        context['author_id'] = author.guid

        if 'text/html' in request.META['HTTP_ACCEPT']:
            return render_to_response('author/stream.html', context)

    else:
        if 'text/html' in request.META['HTTP_ACCEPT']:
            return redirect('/login/')


def friends(request):
    """
    GET: Retrieves all friends of an author
    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
        return render(request, 'login/index.html', context)

    author, _ = Author.objects.get_or_create(user=request.user)

    noRelationshipsAuthors = []

    context = RequestContext(request,
                     { "user" : request.user,
                       "friends": author.getFriends(),
                       "follows": author.getPendingSentRequests(),
                       "followers": author.getPendingReceivedRequests(),
                       "author_id": author.guid })

    return render(request, 'author/friends.html', context)

def searchOtherServers(searchString):
    """
    Searches other servers using their RESTful APIs for authors
    """

    authorsFound = []

    # BenHoboCo
    for server in SERVER_URLS:

        try:
            authorsFO = urllib2.urlopen("%s/api/authors" % server)
            allAuthors = authorsFO.read()
            jsonAllAuthors = json.loads(allAuthors)

            for author in jsonAllAuthors:
                if searchString in author["displayname"]:
                    authorsFound.append(author)
        except urllib2.URLError: # fail silently on connection failure
            pass

    return authorsFound

def search(request):
    """
    GET: Returns author profile based on username search
    """
    context = RequestContext(request)

    # TODO: This should be a GET
    if request.method == 'POST':
        username = request.POST['username']

        users = User.objects.filter(
                    Q(username__contains=username) & ~Q(username=request.user))
        usersAndStatus = []

        author, _ = Author.objects.get_or_create(user=request.user)

        # search locally
        for u in users:
            a, _ = Author.objects.get_or_create(user=u)
            r = LocalRelationship.objects.filter(
                    (Q(author1=author) & Q(author2=a))
                   |(Q(author2=author) & Q(author1=a)))

            # These 2 authors have a relationship
            if len(r) > 0:

                if (r[0].relationship): # They are friends
                    usersAndStatus.append([u.username, "Friend", a.guid])

                else:
                    if r[0].author1 == author:
                        usersAndStatus.append([u.username, "Following", a.guid])
                    else:
                        usersAndStatus.append([u.username, "Follower", a.guid])
            else:
                usersAndStatus.append([u.username, "No Relationship", a.guid])

        authorsOtherServers = searchOtherServers(username)

        # search remotely
        for a in authorsOtherServers:

            #TODO: make sure the url is absolute (includes remote hostname)

            remoteAuthor, _ = RemoteAuthor.objects.get_or_create(
                                    guid=a["id"],
                                    displayName=a["displayname"],
                                    host=a["host"],
                                    url=a["url"])

            r = RemoteRelationship.objects.filter(localAuthor=author,
                                                  remoteAuthor=remoteAuthor)

            # These 2 authors have a relationship
            if len(r) > 0:

                if r[0].relationship == 0: # user follow the author
                    usersAndStatus.append([a["displayname"],
                                           "Following",
                                           a["id"]])

                elif r[0].relationship == 1: # the author follows the user
                    if r[0].localAuthor == author:
                        usersAndStatus.append([a["displayname"],
                                               "Follower",
                                               a["id"]])
                else: # relationship value should be 2: they are friends
                    usersAndStatus.append([a["displayname"],
                                           "Friend",
                                           a["id"]])
            else:
                usersAndStatus.append([a["displayname"],
                                      "No Relationship",
                                      a["id"]])

        context = RequestContext(request, {'searchphrase': username,
                                           'results': usersAndStatus,
                                           'author_id': author.guid})

    return render(request, 'author/search_results.html', context)

def updateRelationship(request, guid):
    """
    POST: Updates the relationship of the current user with <username>
    """

    if request.method == 'POST' and request.is_ajax:

        currentRelationship = request.POST["relationship"]
        requestAuthor, _ = Author.objects.get_or_create(user=request.user)

        # check if the guid is a local or remote user

        author = Author.objects.filter(guid=guid)

        status = currentRelationship

        if len(author) > 0: # author is local

            author = author[0]

            if currentRelationship == "Friend":
                # Unfriend
                relationship = LocalRelationship.objects.get(
                                ((Q(author1=author) & Q(author2=requestAuthor))
                                |(Q(author2=author) & Q(author1=requestAuthor)))
                                &Q(relationship=True))
                relationship.delete()
                LocalRelationship.objects.get_or_create(
                                            author1=author,
                                            author2=requestAuthor,
                                            relationship=False)
                status = "Unfriended"

            elif currentRelationship == "Following":
                # Unfollow
                relationship, _ = LocalRelationship.objects.get_or_create(
                                                   author1=requestAuthor,
                                                   author2=author,
                                                   relationship=False)
                relationship.delete()
                status = "Unfollowed"

            elif currentRelationship == "Follower":
                # Befriend
                relationship, _ = LocalRelationship.objects.get_or_create(
                                                   author1=author,
                                                   author2=requestAuthor)
                relationship.relationship = True
                relationship.save()
                status = "Befriended"

            elif currentRelationship == "No Relationship":
                # Follow
                _, _ = LocalRelationship.objects.get_or_create(
                                                   author1=requestAuthor,
                                                   author2=author,
                                                   relationship=False)
                status = "Followed"

        else: # author is remote (assume it exists remotely)
            # We assume we have already created the RemoteAuthor in our
            # model, either from the REST friend request or from the AJAX
            # on the search page.

            remoteAuthor = RemoteAuthor.objects.filter(guid=guid)

            if len(remoteAuthor) == 0:
                return HttpResponse("Failure: No such GUID: %s" % guid)
            else:
                remoteAuthor = remoteAuthor[0]

            if currentRelationship == "Friend":
                # Unfriend
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.relationship = 1
                relationship.save()
                status = "Unfriended"

            elif currentRelationship == "Following":
                # Unfollow
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.delete()
                status = "Unfollowed"

            elif currentRelationship == "Follower":
                # Befriend
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.relationship = 2
                relationship.save()
                status = "Befriended"

            elif currentRelationship == "No Relationship":
                # Follow
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.relationship = 0
                relationship.save()
                status = "Followed"

        return HttpResponse(status)

    return HttpResponse("success!")

