from django.shortcuts import (get_object_or_404, render, redirect,
                              render_to_response)
from django.http import HttpResponse
from django.template import RequestContext
from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from author.models import Author, Relationship
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from categories.models import Category
from comments.models import Comment
from images.models import Image, ImagePost, ImageVisibilityException

import markdown, json
import uuid

def isUserAccepted(user):
    author = Author.objects.filter(user=user)
    if len(author) > 0:
        return author[0].accepted

    return False

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
        author = Author.objects.get(author_id=author_id)
        user = author.user
        payload = { } # This is what we send in the RequestContext

        payload['author_id'] = author.author_id
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
        payload['author_id'] = author.author_id

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
    author = Author.objects.get(author_id=author_id)

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
    context["author_id"] = author.author_id

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
        context['author_id'] = author.author_id

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
                       "author_id": author.author_id })

    return render(request, 'author/friends.html', context)

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

        for u in users:
            a, _ = Author.objects.get_or_create(user=u)
            r = Relationship.objects.filter(
                    (Q(author1=author) & Q(author2=a))
                   |(Q(author2=author) & Q(author1=a)))

            # These 2 authors have a relationship
            if len(r) > 0:

                if (r[0].relationship): # They are friends
                    usersAndStatus.append([u.username, "Friend", a.author_id])

                else:
                    if r[0].author1 == author:
                        usersAndStatus.append([u.username, "Following", a.author_id])
                    else:
                        usersAndStatus.append([u.username, "Follower", a.author_id])
            else:
                usersAndStatus.append([u.username, "No Relationship", a.author_id])


        context = RequestContext(request, {'searchphrase': username,
                                           'results': usersAndStatus,
                                           'author_id': author.author_id})

    return render(request, 'author/search_results.html', context)

def updateRelationship(request, username):
    """
    POST: Updates the relationship of the current user with <username>
    """
    #context = RequestContext(request)

    if request.method == 'POST' and request.is_ajax:

        currentRelationship = request.POST["relationship"]
        requestAuthor, _ = Author.objects.get_or_create(user=request.user)

        # assume the user exists
        user = User.objects.get(username=username)

        author = Author.objects.get(user=user)
        status = currentRelationship

        if currentRelationship == "Friend":
            # Unfriend
            relationship = Relationship.objects.get(
                                ((Q(author1=author) & Q(author2=requestAuthor))
                                |(Q(author2=author) & Q(author1=requestAuthor)))
                                &Q(relationship=True))
            relationship.delete()
            Relationship.objects.get_or_create(
                                        author1=author,
                                        author2=requestAuthor,
                                        relationship=False)
            status = "Unfriended"

        elif currentRelationship == "Following":
            # Unfollow
            relationship, _ = Relationship.objects.get_or_create(
                                               author1=requestAuthor,
                                               author2=author,
                                               relationship=False)
            relationship.delete()
            status = "Unfollowed"

        elif currentRelationship == "Follower":
            # Befriend
            relationship, _ = Relationship.objects.get_or_create(
                                               author1=author,
                                               author2=requestAuthor)
            relationship.relationship = True
            relationship.save()
            status = "Befriended"

        elif currentRelationship == "No Relationship":
            # Follow
            _, _ = Relationship.objects.get_or_create(
                                               author1=requestAuthor,
                                               author2=author,
                                               relationship=False)
            status = "Followed"

        return HttpResponse(status)

    return HttpResponse("success!")

