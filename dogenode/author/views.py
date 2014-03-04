from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from author.models import Author

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
    """
    GET: Returns the profile page / information of an author.
    POST: Creates a new profile for an author, i.e. an new author.
    PUT: Updates an author's information.
    """
    context = RequestContext(request)
    
    return render(request, 'author/profile.html', context)

def edit_profile(request):
    """
    Renders html page to allow for editing of profile in web browser.
    """
    context = RequestContext(request)
    
    return render(request, 'author/edit_profile.html', context)

def stream(request):
    """
    GET: Returns the stream of an author (all posts by followers)
    """
    context = RequestContext(request)
    
    return render(request, 'author/stream.html', context)

def posts(request):
    """
    GET: Retrieves all posts (of an author?)
    """
    context = RequestContext(request)
    
    return render(request, 'post/posts.html', context)

def friends(request):
    """
    GET: Retrieves all friends of an author
    PUT: ??
    POST: ??
    """
    context = RequestContext(request)
    
    return render(request, 'author/friends.html', context)

def search(request):
    """
    GET: Returns author profile based on username search
    """
    context = RequestContext(request)
    
    return render(request, 'author/search_results.html', context)
