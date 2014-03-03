from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from login.models import Author

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
