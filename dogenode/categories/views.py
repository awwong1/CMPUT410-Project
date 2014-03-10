from django.shortcuts import render, redirect
from django.template import RequestContext
from django.http import HttpResponse

from categories.models import Category

import json

def add(request):
    '''
    POST: Add a new category to Dogenode.
    '''
    context = RequestContext(request)
    status_code = 200

    if request.method == POST:
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

        if ('text/html' in request.META['HTTP_ACCEPT'] or
            'text/html' in requset.META['HTTP_ACCEPT_LANGUAGE']):
            return render('categories.views.categories', context,
                          status=status_code)

        if ('applcation/json' in request.META['HTTP_ACCEPT'] or
            'applcation/json' in requset.META['HTTP_ACCEPT_LANGUAGE']):
            response = HttpResponse(json.dumps(
                                        {'message': context['message']}),
                                    content_type='application/json')
        else:
            response = HttpResponse(context['message'],
                                    content_type='text/plain')

        response.status_code = status_code
        return response
    else:
        return redirect(request.META['HTTP_REFERER'])

def categories(request):
    '''
    GET: Displays all the categories currently stored by Dogenode.
    '''
    return HttpResponse(Categories.objects.all(), content_type='text/plain')

def category(request, category_id):
    '''
    GET: Displays all posts visible to the user which fall under the supplied
         category ID.
    '''
    return redirect('author.views.stream')
