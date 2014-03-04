from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from author.models import Author, Relationship

def isUserAccepted(user):

    author = Author.objects.filter(user=user)
    if len(author) > 0:
        return author[0].accepted

    return False

# Create your views here.
def index(request):

    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        #https://docs.djangoproject.com/en/dev/topics/auth/default/#authenticating-users
        user = authenticate(username=username, password=password)

        if user is not None:

            # the password verified for the user and the user is accepted
            if isUserAccepted(user):
                login(request, user)
                return HttpResponse("User is valid, active and authenticated")
            else:
                return HttpResponse("Server admin has not accepted your"
                                    " registration yet!")
        else:
            # Incorrect username and password
            return HttpResponse("The username and password were incorrect.")

    return render(request, 'login/index.html', context)

def register(request):

    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password1']

        # Check if username already exists
        if len(User.objects.filter(username=username)) > 0:
            context = RequestContext(request, {'registrationStatus':
                "This username is taken!"})
        else:
            if username and password:
                user = User.objects.create_user(username=username,
                                                password=password)
                user.save()
                context = RequestContext(request, {'registrationStatus':
                    "Registration successful!"})

    return render(request, 'login/register.html', context)

def profile(request):
    context = RequestContext(request)
    
    return render(request, 'author/profile.html', context)

def stream(request):
    context = RequestContext(request)
    
    return render(request, 'author/stream.html', context)

def edit_profile(request):
    context = RequestContext(request)
    
    return render(request, 'author/edit_profile.html', context)

def posts(request):
    context = RequestContext(request)
    
    return render(request, 'author/posts.html', context)

def friends(request):

    context = RequestContext(request)

    if not request.user.is_authenticated():
        return render(request, 'login/index.html', context)

    author, _ = Author.objects.get_or_create(user=request.user)

    noRelationshipsAuthors = []

    context = RequestContext(request,
                     { "user" : request.user,
                       "friends": author.getFriends(),
                       "follows": author.getPendingSentRequests(),
                       "followers": author.getPendingReceivedRequests() })

    return render(request, 'author/friends.html', context)

def search(request):
    context = RequestContext(request)
    
    return render(request, 'author/search_results.html', context)

