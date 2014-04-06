from django.conf import settings
from django.shortcuts import (get_object_or_404, render, redirect,
                              render_to_response)
from django.http import HttpResponse
from django.template import RequestContext
from django.db.models import Q
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import ensure_csrf_cookie

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from author.models import (Author, RemoteAuthor,
                           LocalRelationship, RemoteRelationship)
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from categories.models import Category
from comments.models import Comment
from images.models import Image, ImagePost, ImageVisibilityException
from api.views import postFriendRequest
from api.models import AllowedServer

from rest_framework import status

import dateutil.parser
import json
import markdown
import re
import requests
import uuid

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
                return render_to_response('login/index.html', context)
        else:
            # Incorrect username and password
            context['message'] = "Incorrect username and password."
            return render_to_response('login/index.html', context)

    return render_to_response('login/index.html', context)

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

    return render_to_response('login/register.html', context)

def profile(request, author_id):
    """
    GET: Returns the profile page / information of an author.
    """
    if request.user.is_authenticated():
        viewer = Author.objects.get(user=request.user)
        try:
            author = Author.objects.get(guid=author_id)
        except Author.DoesNotExist:
            context = RequestContext(request)
            context['author_id'] = viewer.guid
            if not getRemoteAuthorProfile(context, author_id):
                 # Error conncecting with remote server
                render_to_response('error/doge_error.html', context)
            render_to_response('author/profile.html', context)

        user = author.user
        payload = { } # This is what we send in the RequestContext
        payload['author_id'] = viewer.guid
        payload['firstName'] = user.first_name or ""
        payload['lastName'] = user.last_name or ""
        payload['username'] = user.username
        payload['githubUsername'] = author.githubUsername or ""
        payload['host'] = author.host or ""
        payload['url'] = author.url or request.build_absolute_uri(author.get_absolute_url())
        payload['userIsAuthor'] = (user.username == request.user.username)
        context = RequestContext(request, payload)
        viewer = Author.objects.get(user=User.objects.get(
                username=request.user))
        context['authPosts'] = Post.getViewablePosts(viewer, author)

        return render_to_response('author/profile.html', context)
    else:
        return redirect('/login/')

def getRemoteAuthorProfile(context, author_id):
    """
    Gets remote author info from another host to display on our site.
    If there was a connection problem or author doesn't exist, error
    message will be displayded (doge_error.html).

    TODO XXX: Going to an author's profile should be an ajax request,
              then we can send host with request instead of searching
              through all allowed servers for the author. Also, need
              to find a way to test this.
    """
    servers = AllowedServer.objects.filter()
    for server in servers:
        if server.host[-1] != '/':
            server.host = server.host + '/'
        response = urllib2.urlopen(server.host+"api/"+author_id)
        if response.status_code == status.HTTP_200_OK and response.context is not None:
            data = json.loads(response.context)
            context['firstName'] = ""
            context['lastName'] = ""
            context['username'] = data["displayname"]
            context['githubUsername'] = ""
            context['host'] = data["host"]
            context['url'] = data["url"]
            context['userIsAuthor'] = False
            return True
    return False

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
            newGithubUsername = request.POST['githubUsername']

            user.first_name = newFirstName or user.first_name
            user.last_name = newLastName or user.last_name
            user.save()

            author.githubUsername = newGithubUsername
            author.save()

            payload['successMessage'] = "Profile updated."

            if newPassword:
                if user.check_password(oldPassword):
                    user.set_password(newPassword)
                    user.save()
                else:
                    payload['failureMessage'] = "Old password incorrect."

            if len(author.githubUsername.strip()) == 0:
                Post.objects.filter(origin="https://github.com").delete()
                payload['successMessage'] += " GitHub posts deleted."

        payload['firstName'] = user.first_name or ""
        payload['lastName'] = user.last_name or ""
        payload['username'] = user.username
        payload['author_id'] = author.guid
        payload['githubUsername'] = author.githubUsername or ""

        context = RequestContext(request, payload)
        return render_to_response('author/edit_profile.html', context)
    else:
        return redirect('/login/')

def getAuthorPosts(request, author_id):
    """
    Retrieves all posts made by the author specified and that are visible
    to currently authenticated user

    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
       return render_to_response('login/index.html', context)

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
        visExceptions = PostVisibilityException.objects.filter(
                        post=post)
        authorIds = [e.author.guid for e in visExceptions]
        imageIds = ImagePost.objects.filter(post=post).values_list(
                        'image', flat=True)

        comments.append(Comment.objects.filter(post_ref=post))
        categories.append(Category.objects.filter(id__in=categoryIds))
        visibilityExceptions.append(Author.objects.filter(
                                        guid__in=authorIds))
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
        comments = []
        authors = []
        categories = []
        visibilityExceptions = []
        images = []

        __queryGithubForEvents(author)
        rawposts = list(Post.getAllowedPosts(author, checkFollow=True))

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
                guid__in=authorIds))
            images.append(Image.objects.filter(id__in=imageIds))

            # Convert Markdown into HTML for web browser
            # django.contrib.markup is deprecated in 1.6, so, workaround
            if post.contentType == post.MARKDOWN:
                post.content = markdown.markdown(post.content)

        # Stream payload
        serverPosts = zip(rawposts, authors, comments, categories,
                               visibilityExceptions, images)

        externalPosts = []
        # Get the other server posts:
        servers = AllowedServer.objects.all()

        for server in servers:
            try:
                author = Author.objects.get(user=request.user)
                # another hack because what the heck is going on with /api/
                if server.host == 'http://127.0.0.1:80/':
                    response = requests.get(
                        "{0}api/author/posts?id={1}".format(
                            server.host, author.guid)
                        )
                else:
                    response = requests.get(
                        "{0}author/posts?id={1}".format(
                            server.host, author.guid
                            )
                        )
                response.raise_for_status()
                jsonAllPosts = response.json()['posts']
                # turn into a dummy post
                for jsonPost in jsonAllPosts:
                    externalPosts.append(jsonPost)
            except Exception as e:
                print ("failed to get posts from there,\n{0}".format(e))

        for externalPost in externalPosts:
            serverPosts.append(__rawPostViewConverter(externalPost))

        context['posts'] = serverPosts
        # Make a Post payload
        context['visibilities'] = Post.VISIBILITY_CHOICES
        context['contentTypes'] = Post.CONTENT_TYPE_CHOICES
        context['author_id'] = author.guid

        if 'text/html' in request.META['HTTP_ACCEPT']:
            return render_to_response('author/stream.html', context)

    else:
        if 'text/html' in request.META['HTTP_ACCEPT']:
            return redirect('/login/')

def __rawPostViewConverter(rawpost):
    """
    Attempt to kludge a raw post into a django template post viewable
    I'm so very sorry

    the worst method of checking 'states', let's just go back to first year
    programming and use an integer
    0 = dogenode
    1 = benhobo
    2 = plkr
    anything else = bust
    """
    postData = {'external':True}
    authData = {}
    commentsData = []
    categoriesData = {}
    visibilityExceptionsData = {}
    imagesData = {}

    # parse out external posts stuff
    postState = 0

    if postState == 0:
        try:
            #dogenode test external posts settings
            postData['HTML']="text/html"
            postData['MARKDOWN']="text/x-markdown"
            postData['PLAIN']="text/plain"
            postData['guid']=rawpost['guid']
            postData['title']=rawpost['title']
            postData['description']=rawpost['description']
            postData['content']=rawpost['content']
            postData['visibility']=rawpost['visibility']
            postData['contentType']=rawpost['content-type']
            postData['origin']=rawpost['origin']
            postData['source']=rawpost['source']
            postData['pubDate']=rawpost['pubDate']
            # postData['modifiedDate']=rawpost['modifiedDate']

            # dogenode test external author settings
            authData['displayname']=rawpost['author']['displayname']
            authData['url']=rawpost['author']['url']
            authData['host']=rawpost['author']['host']
            authData['id']=rawpost['author']['id']

            # dogenode test external comments settings
            for rawComment in rawpost['comments']:
                # get nested author
                rawauth = {}
                rawauth['displayname'] = rawComment['author']['displayname']
                rawauth['url'] = rawComment['author']['url']
                rawauth['host'] = rawComment['author']['host']
                rawauth['id'] = rawComment['author']['id']
                # attach with rest of the comment
                adaptcomment = {}
                adaptcomment['author']=rawauth
                adaptcomment['comment']=rawComment['comment']
                adaptcomment['guid']=rawComment['guid']
                adaptcomment['pubDate']=rawComment['pubDate']
                commentsData.append(adaptcomment)

            #print ("doge: succeded parsing post")
        except Exception as e:
            print ("doge: failed to parse post,\n{0}".format(e))
            # postState = 1 # when rest is implemented
            postState = -1

    if (postState == 1):
        #benhobo test external posts settings
        try:
            pass #todo
            #print ("benhobo: succeded parsing post")
        except Exception as e:
            print ("benhobo: failed to parse post,\n{0}".format(e))
            postState = 2

    if (postState == 2):
        #plkr test external posts settings
        try:
            pass #todo
            #print ("plkr: succeded parsing post")
        except Exception as e:
            print( "plkr: failed to parse post,\n{0}".format(e))
            postState == -1

    if postState >= 0:
        unifiedpost = (postData, authData, commentsData, categoriesData,
                   visibilityExceptionsData, imagesData)
    else:
        print("Something didn't parse properly at all!\n\n")
        unifiedpost = None
    return unifiedpost

def friends(request):
    """
    GET: Retrieves all friends of an author
    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
        return redirect('/login/')

    author = Author.objects.get(user=request.user)

    noRelationshipsAuthors = []

    context = RequestContext(request,
                     { "user" : request.user,
                       "friends": author.getFriends(),
                       "follows": author.getPendingSentRequests(),
                       "followers": author.getPendingReceivedRequests(),
                       "author_id": author.guid })

    return render_to_response('author/friends.html', context)

def searchOtherServers(searchString):
    """
    Searches other servers using their RESTful APIs for authors
    """

    authorsFound = []

    # BenHoboCo
    servers = AllowedServer.objects.all()

    for server in servers:

        try:
            #response = requests.get("%s/api/authors" % server.host)
            response = requests.get("%sapi/search" % server.host)
            response.raise_for_status() # Exception on 4XX/5XX response

            jsonAllAuthors = response.json()

            for author in jsonAllAuthors:
                if searchString in author["displayname"]:
                    authorsFound.append(author)
        # fail silently
        except requests.exceptions.RequestException:
            pass

    return authorsFound

def search(request):
    """
    GET: Returns author profile based on username search
    """
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']

        users = User.objects.filter(
                    Q(username__contains=username) & ~Q(username=request.user))
        usersAndStatus = []

        author = Author.objects.get(user=request.user)

        # search locally
        for u in users:
            a = Author.objects.get(user=u)
            r = LocalRelationship.objects.filter(
                    (Q(author1=author) & Q(author2=a))
                   |(Q(author2=author) & Q(author1=a)))

            userStatus = {"displayname": u.username,
                          "relationship": "No Relationship",
                          "guid": a.guid,
                          "host": settings.OUR_HOST}

            # These 2 authors have a relationship
            if len(r) > 0:

                if (r[0].relationship): # They are friends
                    userStatus["relationship"] = "Friend"
                else:
                    if r[0].author1 == author:
                        userStatus["relationship"] = "Following"
                    else:
                        userStatus["relationship"] = "Follower"

            usersAndStatus.append(userStatus)

        authorsOtherServers = searchOtherServers(username)

        # search remotely
        for a in authorsOtherServers:

            #TODO: make sure the url is absolute (includes remote hostname)

            remoteAuthor, _ = RemoteAuthor.objects.get_or_create(guid=a["id"])

            remoteAuthor.update(displayName=a["displayname"],
                                host=a["host"],
                                url=a["url"])

            r = RemoteRelationship.objects.filter(localAuthor=author,
                                                  remoteAuthor=remoteAuthor)

            authorDisplayName = "%s@%s" % (a["displayname"], a["host"])

            userStatus = {"displayname": authorDisplayName,
                          "relationship": "No Relationship",
                          "guid": a["id"],
                          "host": a["host"]}

            # These 2 authors have a relationship
            if len(r) > 0:

                if r[0].relationship == 0: # user follow the author
                    userStatus["relationship"] = "Following"

                elif r[0].relationship == 1: # the author follows the user
                    userStatus["relationship"] = "Follower"

                else: # relationship value should be 2: they are friends
                    userStatus["relationship"] = "Friend"

            usersAndStatus.append(userStatus)

        context = RequestContext(request, {'searchphrase': username,
                                           'results': usersAndStatus,
                                           'author_id': author.guid})

    return render_to_response('author/search_results.html', context)

def updateRelationship(request, guid):
    """
    POST: Updates the relationship of the current user with <username>
    """

    if request.method == 'POST' and request.is_ajax:

        currentRelationship = request.POST["relationship"]
        host = request.POST["host"]
        requestAuthor = Author.objects.get(user=request.user)

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
                postFriendRequest(requestAuthor, remoteAuthor, False)
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.relationship = 1
                relationship.save()
                status = "Unfriended"

            elif currentRelationship == "Following":
                # Unfollow
                postFriendRequest(requestAuthor, remoteAuthor, False)
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.delete()
                status = "Unfollowed"

            elif currentRelationship == "Follower":
                # Befriend
                postFriendRequest(requestAuthor, remoteAuthor)
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.relationship = 2
                relationship.save()
                status = "Befriended"

            elif currentRelationship == "No Relationship":
                # Follow
                postFriendRequest(requestAuthor, remoteAuthor)
                relationship, _ = RemoteRelationship.objects.get_or_create(
                                        localAuthor=requestAuthor,
                                        remoteAuthor=remoteAuthor)
                relationship.relationship = 0
                relationship.save()
                status = "Followed"

        return HttpResponse(status)

    return HttpResponse("success!")


def __queryGithubForEvents(author):
    """
    Queries GitHub events for an author, if the author has a GitHub
    username.  The events are then inserted into the DB if they do not already
    exist.
    """
    if not author.githubUsername:
        return

    headers = {"Connection": "close"}
    if author.githubEventsETag:
        headers["If-None-Match"] = author.githubEventsETag

    params = { }
    try:
        params["client_id"] = settings.GITHUB_CLIENT_ID
        params["client_secret"] = settings.GITHUB_CLIENT_SECRET
    except AttributeError:
        # If there are no GitHub API keys, you only get 60 requests an hour
        pass

    response = None
    for i in range(0,3):
        try:
            response = requests.get("https://api.github.com/users/%s/events" % \
                                    author.githubUsername, headers=headers,
                                    params=params)
            break
        except requests.exceptions.RequestException:
            continue

    # Return on no response or reached RateLimit
    if not response or int(response.headers["X-RateLimit-Remaining"]) == 0:
        return

    if response.status_code == 200:
        # The ETag helps prevent spamming GitHub servers, and it lets us know
        # if anything new has come in.
        author.githubEventsETag = response.headers["ETag"]
        author.save()

        try:
            events = response.json()

            for event in events:
                postObj, _ = Post.objects.get_or_create(guid=event["id"])
                # http://stackoverflow.com/a/199120
                postObj.title = "GitHub %s" % \
                                re.sub(r"(?<=\w)([A-Z])", r" \1",
                                       event["type"])
                postObj.content = __generateGithubEventContent(event)
                postObj.visibility = Post.PRIVATE
                postObj.contentType = Post.HTML
                postObj.origin = "https://github.com"
                # http://stackoverflow.com/a/3908349
                postObj.pubDate = dateutil.parser.parse(event["created_at"])

                AuthorPost.objects.get_or_create(post=postObj, author=author)

                postObj.save()
        except ValueError:
            return
    else:
        # Nothing has changed since the last query
        return


def __generateGithubEventContent(event):
    type = event["type"]
    payload = event["payload"]
    username = event["actor"]["login"]
    repoName = event["repo"]["name"]
    if type == "CommitCommentEvent":
        comment = payload["comment"]
        return format_html("<p><strong>{0}</strong> " \
                           "<a href='{1}' target='_blank'>commented</a> " \
                           "on a commit:</p><p>{2}</p>",
                            username, comment["html_url"],
                            __prettyTrim(comment["body"]))
    elif type == "CreateEvent":
        return format_html("<p><strong>{0}</strong> created a {1}.</p>" \
                           "<p>{2}</p>",
                            username, payload["ref_type"],
                            payload["description"])
    elif type == "DeleteEvent":
        return format_html("<p><strong>{0}</strong> deleted a {1} " \
                           "from {2}.</p>",
                            username, payload["ref_type"], repoName)
    elif type == "ForkEvent":
        return format_html("<p><strong>{0}</strong> forked a " \
                           "<a href='{1}' target='_blank'>repository.</a></p>",
                           username, payload["forkee"]["html_url"])
    elif type == "GollumEvent":
        ret = format_html("<p><strong>{0}</strong> made some changes to the" \
                          " Wiki:</p>", username)
        pages = payload["pages"]

        ret = format_html("{0}<ul>", mark_safe(ret))
        ret = format_html("{0}{1}", mark_safe(ret),
                          format_html_join("\n",
                                "<li><strong><a href='{0}' target='_blank'>" \
                                "{1}</a></strong> was {2}.</li>",
                                ((p["html_url"], p["title"], p["action"])
                                    for p in pages)))
        ret = format_html("{0}</ul>", mark_safe(ret))

        return ret
    elif type == "IssueCommentEvent":
        return format_html("<p><strong>{0}</strong> {1} a " \
                           "<a href='{2}' target='_blank'>comment</a> on Issue #" \
                           "<a href='{3}' target='_blank'>{4}</a>:</p>" \
                           "<p>{5}</p>",
                            username, payload["action"],
                            payload["comment"]["html_url"],
                            payload["issue"]["html_url"],
                            payload["issue"]["number"],
                            __prettyTrim(payload["comment"]["body"]))
    elif type == "IssuesEvent":
        return format_html("<p><strong>{0}</strong> {1} Issue #" \
                           "<a href='{2}' target='_blank'>{3}</a>: {4}.</p>" \
                           "<p>{5}</p>",
                            username, payload["action"],
                            payload["issue"]["html_url"],
                            payload["issue"]["number"],
                            __prettyTrim(payload["issue"]["title"]),
                            __prettyTrim(payload["issue"]["body"]))
    elif type == "MemberEvent":
        member = payload["member"]
        return format_html("<p><strong><a href='{0}' target='_blank'>{1}</a>" \
                           "</strong> was {2} as a collaborator to {3}.</p>",
                            member["html_url"], member["name"],
                            payload["action"], repoName)
    elif type == "PullRequestEvent":
        return format_html("<p>Pull request #<a href='{0}' target='_blank'>" \
                           "{1}</a> was {2}.</p>",
                            payload["pull_request"]["html_url"],
                            payload["number"], payload["action"])
    elif type == "PullRequestReviewCommentEvent":
        return format_html("<p>A <a href='{0}' target='_blank'>comment</a> " \
                           "was created on a pull request:</p>" \
                           "<p>{1}</p>",
                            payload["comment"]["html_url"],
                            __prettyTrim(payload["comment"]["body"]))
    elif type == "PushEvent":
        commits = payload["commits"]
        ret = format_html("<p><strong>{0}</strong> pushed to {1}:</p>",
                          username, repoName)

        ret = format_html("{0}<ul>", mark_safe(ret))
        for c in commits:
            ret = format_html("{0}\n<li>{1}</li>", mark_safe(ret),
                                __prettyTrim(c["message"]))
        ret = format_html("{0}</ul>", mark_safe(ret))

        return ret
    elif type == "ReleaseEvent":
        release = payload["release"]
        return format_html("<p>{0} of {1} was <a href='{2}' target='_blank'>" \
                           "released</a>. ",
                            release["tag_name"], repoName, release["html_url"])
    elif type == "TeamAddEvent":
        what = ""
        where = ""
        if payload["user"]:
            what = payload["user"]["name"]
            where = payload["user"]["html_url"]

        else:
            what = payload["repository"]["full_name"]
            where = payload["repository"]["html_url"]

        return format_html("<p><strong>{0}</strong> was " \
                           "<a href='{1}' target='_blank'>added</a> to the " \
                           "team {2}.</p>",
                            what, where, payload["team"]["name"])
    elif type == "WatchEvent":
        return format_html("<p><strong>{0}</strong> starred {1}.</p>",
                            username, repoName)
    else:
        return format_html("<p><a href='{0}' target='_blank'>{1}</a></p>",
                            event["repo"]["url"],
                            event["repo"]["url"])


def __prettyTrim(text):
    if len(text) > 140:
        return "%s..." % text[0:140]
    else:
        return text
