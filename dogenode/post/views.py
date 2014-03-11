from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render, render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from post.models import Post, PostVisibilityException, AuthorPost, PostCategory
from categories.models import Category
from author.models import Author
from comments.models import Comment

import markdown

def posts(request):
    """
    Retrieves all posts of an author
    """
    context = RequestContext(request)

    if not request.user.is_authenticated():
        return render(request, 'login/index.html', context)

    author = Author.objects.get(user=request.user)
    postIds = AuthorPost.objects.filter(author=author).values_list(
                'post', flat=True)
    posts = Post.objects.filter(id__in=postIds).order_by('pubDate')
    comments = []
    categories = []
    visibilityExceptions = []

    for post in posts:
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

    return render_to_response('post/posts.html', context)

def post(request, post_id):
    """
    Returns a post and displays it in the web browser.
    """    
    if request.user.is_authenticated():
        user = request.user
        author = Author.objects.get(user=request.user)
        post = Post.objects.get(id=post_id) 
        if (post.isAllowedToViewPost(author)):            
            context = RequestContext(request)

            categoryIds = PostCategory.objects.filter(
                            post=post).values_list('category', flat=True)
            authorIds = PostVisibilityException.objects.filter(
                            post=post).values_list('author', flat=True)

            comments = Comment.objects.filter(post_ref=post)
            visibilityExceptions = Author.objects.filter(
                id__in=authorIds)
            categories = Category.objects.filter(id__in=categoryIds)

            # Convert Markdown into HTML for web browser 
            # django.contrib.markup is deprecated in 1.6, so, workaround
            if post.contentType == post.MARKDOWN:
                post.content = markdown.markdown(post.content)

            context['posts'] = [(post, author, comments, categories, 
                                 visibilityExceptions)]

            return render_to_response('post/post.html', context)
        else:
            return redirect('/posts/')
    else:
        return redirect('/login/')

@ensure_csrf_cookie
def add_post(request):
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
        contentType = request.POST.get("contentType", Post.PLAIN)

        categoryNames = categoriesString.split()
        exceptionUsernames = visibilityExceptionsString.split()

        author = Author.objects.get(user=request.user)
        newPost = Post.objects.create(title=title, description=description,
                                      content=content, visibility=visibility,
                                      contentType=contentType)
        newPost.origin = request.build_absolute_uri(newPost.get_absolute_url())
        newPost.save()

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
            except DoesNotExist:
                pass

    return redirect(request.META['HTTP_REFERER'])

def delete_post(request):
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
            post = Post.objects.get(id=post_id)
            comments = Comment.objects.filter(post_ref=post)

            if (AuthorPost.objects.filter(post=post, 
                                          author=author).count() > 0):
                comments.delete();
                post.delete();
            # else: send a message?

        return redirect('/posts/')
    else:
        return redirect('/login/')
