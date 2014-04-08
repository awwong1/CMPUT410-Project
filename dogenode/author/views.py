from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import (get_object_or_404, render, redirect,
                              render_to_response)
from django.template import RequestContext
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import status
from urlparse import urljoin

from api.models import AllowedServer
from api.views import *
from author.models import (Author, RemoteAuthor,
                           LocalRelationship, RemoteRelationship)
from categories.models import Category
from comments.models import Comment
from images.models import Image, ImagePost, ImageVisibilityException
from post.models import Post, PostVisibilityException, AuthorPost, PostCategory

import dateutil.parser
import json
import markdown
import re
import requests
import uuid
import random

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

# List of random doge imgs to make as profile image
doges = ['angrydoge.jpg', 'doge.jpeg', 'happydoge.jpg', 'saddoge.PNG',
        'sketchydoge.jpg', 'spoileddoge.jpg', 'wetkoala.jpg']
def profile(request, author_id):
    """
    GET: Returns the profile page / information of an author.
    """
    if 'text/html' not in request.META['HTTP_ACCEPT']:
        try:
            author = Author.objects.get(guid=author_id)
        except ObjectDoesNotExist:
            return HttpResponse(json.dumps({"message": "User not found", "status": 404}),
                                status=404, content_type="application/json")

        return HttpResponse(json.dumps(author.as_dict()),
                            content_type="application/json")
    else:
        if request.user.is_authenticated():
            viewer = Author.objects.get(user=request.user)
            try:
                author = Author.objects.get(guid=author_id)
            except Author.DoesNotExist:
                context = RequestContext(request)
                context['author_id'] = viewer.guid
                context['doge'] = doges[random.randint(0,6)]
                if not getRemoteAuthorProfile(context, author_id):
                     # Error conncecting with remote server
                    return render_to_response('error/doge_error.html', context)
                return render_to_response('author/remote_profile.html', context)

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
            context['doge'] = doges[random.randint(0,6)]

            return render_to_response('author/profile.html', context)
        else:
            return redirect('/login/')

def getRemoteAuthorProfile(context, author_id):
    """
    Gets remote author info from another host to display on our site.
    If there was a connection problem or author doesn't exist, error
    message will be displayded (doge_error.html).
    """
    context['firstName'] = ""
    context['lastName'] = ""
    context['githubUsername'] = ""
    context['userIsAuthor'] = False

    try:
        remote = RemoteAuthor.objects.get(guid=author_id)
        context['username'] = remote.displayName
        context['host'] = remote.host
        context['url'] = remote.url
       
        return True
    except Author.DoesNotExist:
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
    if 'application/json' in request.META['HTTP_ACCEPT']:
        return getAuthorPostsAsJSON(request, author_id)
    elif 'text/html' in request.META['HTTP_ACCEPT']:
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
    else:
        return getAuthorPostsAsJSON(request, author_id)

def stream(request):
    """
    Returns the stream of an author (all posts author can view)
    If calling the function restfully, call by sending a GET request to /author/posts
    """
    if 'application/json' in request.META['HTTP_ACCEPT']:
        return getStream(request)
    elif 'text/html' in request.META['HTTP_ACCEPT']:
        if request.user.is_authenticated():
            context = RequestContext(request)
            author = Author.objects.get(user=request.user)
            comments = []
            authors = []
            categories = []
            visibilityExceptions = []
            images = []
            unlinkedImages = []

            linkedImageIds = ImagePost.objects.all().values_list('image', flat=True)
            unlinkedImageObjs = Image.objects.filter(Q(author=author), ~Q(id__in=linkedImageIds))

            for u in unlinkedImageObjs:
                unlinkedImages.append(u.as_dict())

            githubTemplateItems = cache.get('ge-'.join(author.guid)) or []

            # If cache is empty, force a GET request on GitHub
            if len(githubTemplateItems) == 0:
                githubTemplateItems = __queryGithubForEvents(author, useETag=False)

            rawposts = list(Post.getAllowedPosts(author, checkFollow=True))

            for post in rawposts:
                categoryIds = PostCategory.objects.filter(
                    post=post).values_list('category', flat=True)
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
                params = {"id": author.guid}
                headers = {"accept": "application/json"}
                try:
                    # another hack because what the heck is going on with /api/
                    if server.host == 'http://127.0.0.1:80/':
                        url = urljoin(server.host, "api/author/posts")
                        response = requests.get(url, headers=headers, params=params)
                    else:
                        url = urljoin(server.host, "author/posts")
                        response = requests.get(url, headers=headers, params=params)

                    response.raise_for_status()
                    jsonAllPosts = response.json()['posts']
                    # turn into a dummy post
                    for jsonPost in jsonAllPosts:
                        externalPosts.append(jsonPost)
                except Exception as e:
                    # print ("failed to get posts from {1},\n{0}".format(e, server))
                    # may cause IO error, commented out for stability
                    pass

            for externalPost in externalPosts:
                parsedPost = rawPostViewConverter(externalPost)
                if parsedPost != None:
                    serverPosts.append(parsedPost)

            context['posts'] = serverPosts + githubTemplateItems

            # In-place sort the posts by most recent pubDate
            context['posts'].sort(key=lambda x: x[0]['pubDate'], reverse=True)

            # Make a Post payload
            context['visibilities'] = Post.VISIBILITY_CHOICES
            context['contentTypes'] = Post.CONTENT_TYPE_CHOICES
            context['author_id'] = author.guid
            context['unlinked_images'] = unlinkedImages

            if 'text/html' in request.META['HTTP_ACCEPT']:
                return render_to_response('author/stream.html', context)
        else:
            if 'text/html' in request.META['HTTP_ACCEPT']:
                return redirect('/login/')
    else:
        return getStream(request)

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
                       "our_host": settings.OUR_HOST,
                       "author_id": author.guid })

    return render_to_response('author/friends.html', context)

def searchOtherServers(searchString):
    """
    Searches other servers using their RESTful APIs for authors
    """

    authorsFound = []

    servers = AllowedServer.objects.all()

    for server in servers:

        # BenHoboCo
        if "benhoboco" in server.name.lower():
            try:
                response = requests.get("%sapi/authors" % server.host)
                #response = requests.get("%sapi/search" % server.host)
                response.raise_for_status() # Exception on 4XX/5XX response

                jsonAllAuthors = response.json()
                for author in jsonAllAuthors:
                    if searchString in author["displayname"]:
                        authorsFound.append(author)
            # fail silently
            except requests.exceptions.RequestException:
                pass

        elif "plkr" in server.name.lower():
            try:
                response = requests.get("%sapi/search?query=%s" %
                                                (server.host, searchString))
                response.raise_for_status() # Exception on 4XX/5XX response

                jsonAllAuthors = response.json()

                authorsFound.extend(jsonAllAuthors)
            # fail silently
            except requests.exceptions.RequestException:
                pass
        else:
            try:
                response = requests.get("%sapi/search?query=%s" %
                                                (server.host, searchString))
                response.raise_for_status() # Exception on 4XX/5XX response

                jsonAllAuthors = response.json()

                authorsFound.extend(jsonAllAuthors)
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


def __queryGithubForEvents(author, useETag=True):
    """
    Queries GitHub events for an author, if the author has a GitHub
    username.
    """
    templateItems = []
    if not author.githubUsername:
        return templateItems

    headers = {"Connection": "close"}
    if author.githubEventsETag and useETag:
        headers["If-None-Match"] = author.githubEventsETag

    params = { }
    try:
        params["client_id"] = settings.GITHUB_CLIENT_ID
        params["client_secret"] = settings.GITHUB_CLIENT_SECRET
    except AttributeError:
        # If there are no GitHub API keys, you only get 60 requests an hour
        print "WARNING: No API key supplied!  You may get nothing from GitHub!"
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
        return templateItems

    if response.status_code == 200:
        # The ETag helps prevent spamming GitHub servers, and it lets us know
        # if anything new has come in.
        author.githubEventsETag = response.headers["ETag"]
        author.save()

        try:
            events = response.json()

            for event in events:
                post = { }
                post["guid"] = event["id"]
                # http://stackoverflow.com/a/199120
                post["title"] = "GitHub %s" % \
                                re.sub(r"(?<=\w)([A-Z])", r" \1",
                                       event["type"])
                post["content"] = __generateGithubEventContent(event)
                post["visibility"] = Post.PRIVATE
                post["contentType"] = Post.HTML
                post["origin"] = "https://github.com"
                post["pubDate"] = dateutil.parser.parse(event["created_at"])

                templateItems.append((post, author, [], [], [], []))

            cache.set('ge-'.join(author.guid), templateItems, None)
            return templateItems
        except ValueError:
            return templateItems
    else:
        if response.status_code != 304:
            print "WARNING: Status code returned was %d" % response.status_code

        templateItems = cache.get('ge-'.join(author.guid)) or []
        return templateItems


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
