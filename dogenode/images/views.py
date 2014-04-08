import os, mimetypes

from django.core.files import File
from django.contrib.auth.models import User
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render, render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.contrib.staticfiles import views

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from author.models import Author
from images.models import Image, ImageVisibilityException

import json

@login_required
def getViewableImages(request):
    context = RequestContext(request)

    if request.user.is_authenticated():
        images = Image.objects.all()
        author = Author.objects.get(user=request.user)

        viewableImageUrls = []

        for image in images:
            if image.isAllowedToViewImage(author):
                viewableImageUrls.append(image.get_absolute_url())

        context['image_urls'] = viewableImageUrls
        context['author_id'] = author.guid
    else:
        images = Image.objects.filter(visibility=Image.PUBLIC)
        context['image_urls'] = [image.get_absolute_url() for image in images]

    return render_to_response('images/images.html', context)


@login_required
def uploadImage(request):
    author = Author.objects.get(user=request.user)

    if request.method == "POST":
        images = request.FILES.getlist('image')
        visibility = request.POST.get('visibility', Image.PRIVATE)
        visibilityExceptionsString = request.POST.get("visibilityExceptions",
                                                      "")
        exceptionUsernames = visibilityExceptionsString.split()

        jsonPayload = []
        htmlPayload = []

        for image in images:
            newImage = Image.objects.create(author=author, file=image,
                                            visibility=visibility,
                                            contentType=image.content_type)
            if newImage:
                for u in exceptionUsernames:
                    exceptionUser = User.objects.get(username=u)
                    exceptionAuthor = Author.objects.get(user=exceptionUser)

                    ImageVisibilityException.objects.get_or_create(
                                    image=newImage, author=exceptionAuthor)

                jsonPayload.append(newImage.as_dict())
                htmlPayload.append(newImage.get_absolute_url())

        if 'application/json' in request.META['HTTP_ACCEPT']:
            return HttpResponse(json.dumps(jsonPayload), status=201,
                                content_type="application/json")
        elif 'text/html' in request.META['HTTP_ACCEPT']:
            return redirect('/author/posts/')
        else:
            return HttpResponse(json.dumps(jsonPayload), status=201,
                                content_type="application/json")
    else:
        context = RequestContext(request)
        context['author_id'] = author.guid

        return render_to_response('images/upload.html', context)


@login_required
def getImagesByAuthor(request, author_guid):
    return HttpResponse("OK")


def getImage(request, author_guid, image_name):
    # Find the file, read it, and send it as an 
    # HTTPResponse object

    try:
        imagePath = author_guid + "/" + image_name
        image = Image.objects.get(file=imagePath)
        content_type = mimetypes.guess_type(image.file.path)
    except Image.DoesNotExist:
        return views.serve(request, 'images/not_found.png')

    if request.user.is_authenticated():
        author = Author.objects.get(user=request.user)

        if image.isAllowedToViewImage(author):
            with open(image.file.path, 'rb') as f:
                return HttpResponse(f.read(), content_type=content_type)
        else:
            return views.serve(request, 'images/not_allowed.png')
    else:
        if image.visibility == Image.PUBLIC:
            with open(image.file.path, 'rb') as f:
                return HttpResponse(f.read(), content_type=content_type)
        else:
            return views.serve(request, 'images/not_allowed.png')
