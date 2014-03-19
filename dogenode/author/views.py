from django.shortcuts import get_object_or_404, render, redirect, render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from django.db.models import Q

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from author.models import Author, Relationship
from post.views import makeJSONPost
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from categories.models import Category
from comments.models import Comment

import markdown, json

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

def logUserOut(request):
    context = RequestContext(request)
    logout(request)
    return render(request, 'login/index.html', context)

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

def profile(request, username):
    """
    GET: Returns the profile page / information of an author.
    """
    if request.user.is_authenticated():
        user = User.objects.get(username=username)
        author = Author.objects.get(user=user)
        payload = { } # This is what we send in the RequestContext

        payload['firstName'] = user.first_name or ""
        payload['lastName'] = user.last_name or ""
        payload['username'] = user.username
        payload['aboutMe'] = author.about_me or ""
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
            newAboutMe = request.POST['aboutMe']

            user.first_name = newFirstName or user.first_name
            user.last_name = newLastName or user.last_name
            user.save()

            author.about_me = newAboutMe
            author.save()

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
        payload['aboutMe'] = author.about_me or ""

        context = RequestContext(request, payload)
        return render(request, 'author/edit_profile.html', context)
    else:
        return redirect('/login/')

def getAuthorPosts(request, author_id):
    """
    Retrieves all posts made by the author specified and that are visible
    to currently authenticated user

    To get the json representation: http://service/author/author_id/posts
    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
        if 'application/json' in request.META['HTTP_ACCEPT']:
            return HttpResponse(status=401)
        else:
           return render(request, 'login/index.html', context)

    viewer = Author.objects.get(user=request.user)
    author = Author.objects.get(id=author_id)

    postIds = AuthorPost.objects.filter(author=author).values_list(
                'post', flat=True)
    posts = Post.getViewablePosts(viewer, author)
    comments = []
    categories = []
    authors = []   #  for the sake of making makeJSONPost work
    visibilityExceptions = []

    for post in posts:
        authors.append(author)
        categoryIds = PostCategory.objects.filter(post = post).values_list(
                        'category', flat=True)
        authorIds = PostVisibilityException.objects.filter(
                        post=post).values_list('author', flat=True)

        comments.append(Comment.objects.filter(post_ref=post))
        categories.append(Category.objects.filter(id__in=categoryIds))
        visibilityExceptions.append(Author.objects.filter(
                                        id__in=authorIds))

        # Convert Markdown into HTML for web browser 
        # django.contrib.markup is deprecated in 1.6, so, workaround
        if post.contentType == post.MARKDOWN:
            post.content = markdown.markdown(post.content)

    context["posts"] = zip(posts, comments, categories, visibilityExceptions)
    data = {"posts":posts, 
            "comments":comments, 
            "categories":categories,
            "authors": authors}

    if 'text/html' in request.META['HTTP_ACCEPT'] and viewer == author:
        return render_to_response('post/posts.html', context)

    elif 'application/json' in request.META['HTTP_ACCEPT']:
        response = HttpResponse(makeJSONPost(data),
                                content_type="application/json",
                                status=status.HTTP_200_OK)
    else:
        response = HttpResponse(status=status.HTTP_401_UNAUTHORIZED)

    return response

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

        for post in rawposts:
            categoryIds = PostCategory.objects.filter(post=post).values_list(
                            'category', flat=True)
            authorIds = PostVisibilityException.objects.filter(
                            post=post).values_list('author', flat=True)

            authors.append(AuthorPost.objects.get(post=post).author)
            comments.append(Comment.objects.filter(post_ref=post))
            categories.append(Category.objects.filter(id__in=categoryIds))
            visibilityExceptions.append(Author.objects.filter(
                id__in=authorIds))

            # Convert Markdown into HTML for web browser 
            # django.contrib.markup is deprecated in 1.6, so, workaround
            if post.contentType == post.MARKDOWN:
                post.content = markdown.markdown(post.content)

        # Stream payload
        context['posts'] = zip(rawposts, authors, comments, categories, 
                               visibilityExceptions)
        # Make a Post payload
        context['visibilities'] = Post.VISIBILITY_CHOICES
        context['contentTypes'] = Post.CONTENT_TYPE_CHOICES

        data = {"posts":rawposts, 
                "comments":comments, 
                "categories":categories,
                "authors":authors}

        if 'text/html' in request.META['HTTP_ACCEPT']:
            return render_to_response('author/stream.html', context)

        elif 'application/json' in request.META['HTTP_ACCEPT']:
            return  HttpResponse(makeJSONPost(data),
                                content_type="application/json",
                                status=status.HTTP_200_OK)
    else:
        if 'text/html' in request.META['HTTP_ACCEPT']:
            return redirect('/login/')

        elif 'application/json' in request.META['HTTP_ACCEPT']:
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED)

def areFriends(request, userid1, userid2):

    user1 = User.objects.filter(id=userid1)
    user2 = User.objects.filter(id=userid2)

    if len(user1) > 0 and len(user2) > 0:

        author1, _ = Author.objects.get_or_create(user=user1[0])
        author2, _ = Author.objects.get_or_create(user=user2[0])

        if author2 in author1.getFriends():
            return HttpResponse('{"query":"friends",'
                    '"friends":[%s, %s]}' % (userid1, userid2))

    return HttpResponse('{"query":"friends",'
            '"friends":"NO"}')

# The POST request is sent to a url which includes the user ID, but the user
# ID is also sent in the POST request body.
# Right now I am using the user ID sent in the request body
def getFriendsFromList(request, userid):

    if request.method == 'POST':
        #data = json.loads(request.raw_post_data)

        userid = request.POST['author']
        user = User.objects.filter(id=userid)

        if len(user) > 0:

            author, _ = Author.objects.get_or_create(user=user)

            friendUserids = [a.user.id for a in author.getFriends()]
            
            friends = (set(friendUserids) &
                       set(request.POST.getlist("authors")))

            return HttpResponse('{"query":"friends",'
                                '"author":"%s",'
                                '"friends":"%s"}' % (userid, friends))

    # Either this request wasn't a POST or the POSTed userid was not found
    return HttpResponse('{"query":"friends",'
                        '"author":"%s",'
                        '"friends":"[]"}' % userid)

def friends(request):
    """
    GET: Retrieves all friends of an author
    PUT: ??
    POST: ??
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
                       "followers": author.getPendingReceivedRequests() })

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
                    usersAndStatus.append([u.username, "Friend"])

                else:
                    if r[0].author1 == author:
                        usersAndStatus.append([u.username, "Following"])
                    else:
                        usersAndStatus.append([u.username, "Follower"])
            else:
                usersAndStatus.append([u.username, "No Relationship"])


        context = RequestContext(request, {'searchphrase': username,
                                           'results': usersAndStatus})

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

        author, _ = Author.objects.get_or_create(user=user)

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
        
