from django.shortcuts import render
from django.template import RequestContext

# Create your views here.
def index(request):
    context = RequestContext(request)
    
    return render(request, 'author/stream.html', context)


def profile(request):
    context = RequestContext(request)
    
    return render(request, 'author/profile.html', context)

def edit_profile(request):
    context = RequestContext(request)
    
    return render(request, 'author/edit_profile.html', context)

def posts(request):
    context = RequestContext(request)
    
    return render(request, 'author/posts.html', context)

def friends(request):
    context = RequestContext(request)
    
    return render(request, 'author/friends.html', context)

def search(request):
    context = RequestContext(request)
    
    return render(request, 'author/search_results.html', context)
