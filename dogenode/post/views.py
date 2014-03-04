from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
# Create your views here.

def posts(request):
    context = RequestContext(request)
    
    return render(request, 'post/posts.html', context)

