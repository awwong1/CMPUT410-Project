from django.shortcuts import get_object_or_404, render, redirect, render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from django.db.models import Q

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from author.models import Author, Relationship
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from categories.models import Category
from comments.models import Comment

import markdown, json

def isUserAccepted(user):

    author = Author.objects.filter(user=user)
    if len(author) > 0:
        return author[0].accepted

    return False

# Create your views here.
def index(request):

    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        #https://docs.djangoproject.com/en/dev/topics/auth/default/#authenticating-users
        user = authenticate(username=username, password=password)

        if user is not None:

            # the password verified for the user and the user is accepted
            if isUserAccepted(user):
                login(request, user)
                return redirect('/author/stream/')
            else:
                context = RequestContext(request,
                                {'message': ("Server admin has not accepted"
                                             " your registration yet!") })
                return render(request, 'login/index.html', context)
        else:
            # Incorrect username and password
            context = RequestContext(request,
                            {'message': "Incorrect username and password." })
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
        return render(request, 'author/profile.html', context)
    else:
        return redirect('/login/')

def edit_profile(request):
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

def stream(request):
    """
    GET: Returns the stream of an author (all posts by followers)
    """
    if request.user.is_authenticated():
        context = RequestContext(request)
        author = Author.objects.get(user=request.user)
        # rawposts = Post.objects.all().order_by('pubDate')
        rawposts = Post.getAllowedPosts(author)
        comments = []
        authors = []

        for post in rawposts:
            authors.append(AuthorPost.objects.get(post=post).author)
            comments.append(Comment.objects.filter(post_ref=post))

            # Convert Markdown into HTML for web browser 
            # django.contrib.markup is deprecated in 1.6, so, workaround
            if post.contentType == post.MARKDOWN:
                post.content = markdown.markdown(post.content)

        context['posts'] = zip(rawposts, authors, comments)
        context['visibilities'] = Post.VISIBILITY_CHOICES
        context['contentTypes'] = Post.CONTENT_TYPE_CHOICES
        return render_to_response('author/stream.html', context)
    else:
        return redirect('/login/')

def posts(request):
    """
    GET: Retrieves all posts (of an author?)
    """
    context = RequestContext(request)
    
    return render(request, 'post/posts.html', context)

def areFriends(request, username1, username2):

    user1 = User.objects.filter(username=username1)
    user2 = User.objects.filter(username=username2)

    if len(user1) > 0 and len(user2) > 0:
        
        author1, _ = Author.objects.get_or_create(user=user1[0])
        author2, _ = Author.objects.get_or_create(user=user2[0])

        if author2 in author1.getFriends():
            return HttpResponse('{"query":"friends",'
                    '"friends":[%s, %s]}' % (username1, username2))

    return HttpResponse('{"query":"friends",'
            '"friends":"NO"}')

def getFriendsFromList(request, username):

    if request.method == 'POST':
        #data = json.loads(request.raw_post_data)

        username = request.POST['author']
        user = User.objects.filter(username=username)

        if len(user) > 0:
            author, _ = Author.objects.get_or_create(user=user)

            friendUsernames = [a.user.username for a in author.getFriends()]
            
            friends = (set(friendUsernames) &
                       set(request.POST.getlist("authors")))

            return HttpResponse('{"query":"friends",'
                                '"author":"%s",'
                                '"friends":"%s"}' % (username, friends))

    # Either this request wasn't a POST or the POSTed username was not found
    return HttpResponse('{"query":"friends",'
                        '"author":"%s",'
                        '"friends":"[]"}' % username)


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

