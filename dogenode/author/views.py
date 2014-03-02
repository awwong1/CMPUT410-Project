from django.shortcuts import render
from django.template import RequestContext

# Create your views here.
def index(request):
    context = RequestContext(request)
    
    return render(request, 'author/stream.html', context)
