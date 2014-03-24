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
from author.models import Author
from comments.models import Comment

import markdown
import json


def getPost(request, post_id):
    """
    Returns a post and displays it in the web browser if the request
    HTTP_ACCEPT header was set to text/html. The currently authenticated
    user must also have permissions to view the post, else it will not be
    shown.

    If the request HTTP_ACCEPT header was set to json, then the json
    representation of the post will be returned. This representation could
    be accessed by http://service/posts/{post_id}, which would return a list
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

            categoryIds = PostCategory.objects.filter(
                            post=post).values_list('category', flat=True)
            authorIds = PostVisibilityException.objects.filter(
                            post=post).values_list('author', flat=True)
            imageIds = ImagePost.objects.filter(post=post).values_list(
                            'image', flat=True)

            postAuthor = AuthorPost.objects.get(post=post).author

            comments = Comment.objects.filter(post_ref=post)
            visibilityExceptions = Author.objects.filter(
                id__in=authorIds)
            categories = Category.objects.filter(id__in=categoryIds)
            images = Image.objects.filter(id__in=imageIds)

            # Convert Markdown into HTML for web browser
            # django.contrib.markup is deprecated in 1.6, so, workaround
            if post.contentType == post.MARKDOWN:
                post.content = markdown.markdown(post.content)

            context['posts'] = [(post, postAuthor, comments, categories,
                                 visibilityExceptions, images)]
            context['author_id'] = author.author_id

            return render_to_response('post/post.html', context)
    else:
        return redirect('/login/')

def getAllPublicPosts(request):
    """
    Retreives all public posts.
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
    context['author_id'] = author.author_id
    return render_to_response('post/public_posts.html', context)

def handlePost(request, post_id):
    if request.method == "GET" or request.method == "POST":
        return getPost(request, post_id)

@ensure_csrf_cookie
def addFormPost(request):
    """
    Adds a new post and displays
    """
    context = RequestContext(request)

    if request.method == "POST":
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        content = request.POST.get("content", "")
        visibility = request.POST.get("visibility", Post.PRIVATE)
        visibilityExceptionsString = request.POST.get("visibilityExceptions",
                                                      "")
        categoriesString = request.POST.get("categories", "")
        contentType = request.POST.get("content-type", Post.PLAIN)

        images = request.FILES.getlist('image')

        categoryNames = categoriesString.split()
        exceptionUsernames = visibilityExceptionsString.split()

        author = Author.objects.get(user=request.user)
        newPost = Post.objects.create(title=title, description=description,
                                      content=content, visibility=visibility,
                                      contentType=contentType)
        newPost.origin = request.build_absolute_uri(newPost.get_absolute_url())
        newPost.save()

        # If there are also images, handle that too
        for image in images:
            newImage = Image.objects.create(author=author, file=image,
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
                for image in images:
                    ImageVisibilityException.objects.get_or_create(
                            image=newImage, author=authorObject)
            except ObjectDoesNotExist:
                pass

    return redirect(request.META['HTTP_REFERER'])

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

        return redirect('/author/'+str(author.author_id)+'/posts/')
    else:
        return redirect('/login/')
