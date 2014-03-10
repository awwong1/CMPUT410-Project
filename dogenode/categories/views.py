from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponse

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from categories.models import Category
from post.models import Post, PostCategory
from author.models import Author

import json

@csrf_exempt
def add(request):
    '''
    POST: Add a new category to Dogenode.  Does not need a CSRF token, so that
          means anyone can create new categories with POST requests.
    '''
    context = RequestContext(request)
    status_code = 200

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            obj, created = Category.objects.get_or_create(name=name.lower())
            if created:
                context['message'] = "%s added to Dogenode!" % obj.name
            else:
                context['message'] = "%s already exists!" % obj.name
                status_code = 409 # Conflict
        else:
            context['message'] = "A name is required."

        if 'text/html' in request.META['HTTP_ACCEPT']:
            return render('categories.views.categories', context,
                          status=status_code)

        if 'application/json' in request.META['HTTP_ACCEPT']:
            response = HttpResponse(json.dumps(
                                        {'message': context['message']}),
                                    content_type='application/json',
                                    status=status_code)
        else:
            response = HttpResponse(context['message'],
                                    content_type='text/plain',
                                    status=status_code)

        return response
    else:
        return redirect(request.META['HTTP_REFERER'])

def categories(request):
    '''
    GET: Displays all the categories currently stored by Dogenode.
    '''
    if 'text/html' in request.META['HTTP_ACCEPT']:
        response = HttpResponse(content_type='text/html')
        response.write('<!DOCTYPE html><html><body><ul>')
        [response.write("<li>%i: %s</li>" % (obj.id, obj.name)) for obj in Category.objects.all()]
        response.write('</ul></body></html>')

        return response

    elif 'application/json' in request.META['HTTP_ACCEPT']:
        return HttpResponse(json.dumps([obj.as_dict() for obj in Category.objects.all()]),
                            content_type='application/json')

    else:
        return HttpResponse(["%s " % obj for obj in Category.objects.all()],
                            content_type='text/plain')

def category(request, category_id):
    '''
    GET: Displays all posts visible to the user which fall under the supplied
         category ID.
    '''
    if not request.user.is_authenticated():
        return redirect('/login/')

    author = Author.objects.get(user=request.user)
    allAllowedPosts = Post.getAllowedPosts(author)

    try:
        category = Category.objects.get(id=int(category_id))
        postIds = PostCategory.objects.filter(post__in=allAllowedPosts, category=category).values_list('post', flat=True)
        postsWithCategory = Post.objects.filter(id__in=postIds)
    except DoesNotExist:
        redirect('author.views.stream')

    return HttpResponse(["%s\n" % obj.content for obj in postsWithCategory],
                        content_type='text/plain')
