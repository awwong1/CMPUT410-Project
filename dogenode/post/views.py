from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render, render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from images.models import Image, ImagePost, ImageVisibilityException
from categories.models import Category
from author.models import Author, RemoteAuthor
from comments.models import Comment

import markdown
import json
import urllib2
import datetime
import base64

def getJSONPost(viewer_id, post_id, host): 
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

    if post.visibility == Post.PUBLIC:
        return (True, post)

    # dealing with local authors
    if len(Author.objects.filter(guid=viewer_id)) > 0:
        return (post.isAllowedToViewPost(Author.objects.get(guid=viewer_id)),
                post)

    # dealing with remote authors
    viewerObj = RemoteAuthor.objects.get_or_create(guid=viewer_id, host=host)
    viewer = viewerObj[0]
    viewerGuid = viewer.guid[0]
    viewable = False

    if post.visibility == Post.SERVERONLY:
        if host == OUR_HOST:    
            viewable = True
    elif post.visibility == Post.FOAF:
        authorFriends = postAuthor.getFriends()
        allFriends = authorFriends["remote"] + authorFriends["local"]
        for friend in authorFriends["local"]:
            response = urllib2.urlopen("%s/api/friends/%s/%s" % 
                                        (friend.host,   
                                        str(viewerGuid),
                                        str(postAuthor.guid)))
            if json.loads(response)["friends"] != "NO":
                viewable = True
                break 
    elif post.visibility == Post.FRIENDS:
        if viewer in postAuthor.getFriends()["remote"]:
            viewable = True
    elif post.visibility == Post.PRIVATE:
        if viewerGuid == postAuthor.guid:
            viewable = True

    return (viewable, post)

def getPost(request, post_id):
    """
    Returns a post and displays it in the web browser if the request
    be accessed by http://service/post/{post_id}, which would return a list
    of posts containing the requested post. If the currently authenticated
    user does not have the permission to view the post, the list will be
    empty.
    """
    if request.user.is_authenticated():
        user = request.user
        author = Author.objects.get(user=request.user)
        post = Post.objects.get(guid=post_id)
        if (post.isAllowedToViewPost(author)):
            context = RequestContext(request)
            components = getPostComponents(post);

            # Convert Markdown into HTML for web browser
            # django.contrib.markup is deprecated in 1.6, so, workaround
            if post.contentType == post.MARKDOWN:
                post.content = markdown.markdown(post.content)

            context['posts'] = [(post, postAuthor, components["comments"], 
                                components["categories"],
                                components["visibilityExceptions"], 
                                components["images"])]
            context['author_id'] = author.guid

            return render_to_response('post/post.html', context)
    else:
        return redirect('/login/')

def getPostComponents(post):
    """
    Gets all componenets of a post, including images, comments, categories,
    and visibility exceptions.

    Returns a dictionary containing all the information.
    """
    components = {}
    categoryIds = PostCategory.objects.filter(
                    post=post).values_list('category', flat=True)
    authorIds = PostVisibilityException.objects.filter(
                    post=post).values_list('author', flat=True)
    imageIds = ImagePost.objects.filter(post=post).values_list(
                    'image', flat=True)

    postAuthor = AuthorPost.objects.get(post=post).author

    components["comments"] = Comment.objects.filter(post_ref=post)
    components["visibilityExceptions"] = Author.objects.filter(
        guid__in=authorIds)
    components["categories"] = Category.objects.filter(id__in=categoryIds)
    components["images"] = Image.objects.filter(id__in=imageIds)

    return components

def getAllPublicPosts(request):
    """
    Retreives all public posts and displays it on the web browser
    """
    context = RequestContext(request)
    author = Author.objects.get(user=request.user)
    rawposts = Post.objects.filter(visibility=Post.PUBLIC)
    comments = []
    authors = []
    categories = []
    images = []

    for post in rawposts:
        categoryIds = PostCategory.objects.filter(post=post).values_list(
                        'category', flat=True)
        imageIds = ImagePost.objects.filter(post=post).values_list(
                        'image', flat=True)

        authors.append(AuthorPost.objects.get(post=post).author)
        comments.append(Comment.objects.filter(post_ref=post))
        categories.append(Category.objects.filter(id__in=categoryIds))
        images.append(Image.objects.filter(id__in=imageIds))

    # Stream payload
    context['posts'] = zip(rawposts, authors, comments, categories, images)
    context['author_id'] = author.guid
    return render_to_response('post/public_posts.html', context)

def handlePost(request, post_id):
    if request.method == "GET" or request.method == "POST":
        return getPost(request, post_id)

def createPost(request, post_id, data):
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
    images = data.get("images")

    categoryNames = categoriesString.split()
    exceptionUsernames = visibilityExceptionsString.split()
    author = Author.objects.get(user=request.user)
    newPost = Post.objects.create(guid=guid, title=title,
                                  description=description,
                                  content=content, visibility=visibility,
                                  contentType=contentType)
    newPost.origin = request.build_absolute_uri(newPost.get_absolute_url())
    newPost.save()

    # If there are also images, handle that too
    for image in images:
        # decoding base64 image code from: https://gist.github.com/yprez/7704036
        # base64 encoded image - decode
        format, imgstr = data.split(';base64,')  # format ~= data:image/X,
        ext = format.split('/')[-1]  # guess file extension
        decoded = ContentFile(base64.b64decode(imgstr), name="img." + ext)
        newImage = Image.objects.create(author=author, file=decoded,
                                        visibility=visibility,
                                        contentType=image.content_type)
        ImagePost.objects.create(image=newImage, post=newPost)

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
            #for image in images:
            #    ImageVisibilityException.objects.get_or_create(
            #            image=newImage, author=authorObject)
        except ObjectDoesNotExist:
            pass

    return newPost

def updatePost(post, data):
    """ 
    Completely updates or partially updates a post given post data in
    json format.
    """
    for key, value in data.items():
        setattr(post, key, value)
    post.modifiedDate = datetime.datetime.now()
    post.save()
    return post

def deletePost(request):
    """
    Deletes the Post based on the post id given in the request.
    Returns the user back to their posts page.
    """
    if request.user.is_authenticated():
        context = RequestContext(request)
        user = request.user
        author = Author.objects.get(user=request.user)
        if request.method == "POST":
            post_id = request.POST["post_id"]
            post = Post.objects.get(guid=post_id)
            comments = Comment.objects.filter(post_ref=post)

            if (AuthorPost.objects.filter(post=post,
                                          author=author).count() > 0):
                comments.delete();
                post.delete();
            # else: send a message?

        return redirect('/author/'+str(author.guid)+'/posts/')
    else:
        return redirect('/login/')
