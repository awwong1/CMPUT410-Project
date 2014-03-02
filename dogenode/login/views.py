from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import RequestContext

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

# Create your views here.
def index(request):

    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        #https://docs.djangoproject.com/en/dev/topics/auth/default/#authenticating-users
        user = authenticate(username=username, password=password)

        if user is not None:
            # the password verified for the user
            if user.is_active:
                return HttpResponse("User is valid, active and authenticated")
            else:
                return HttpResponse("Account disabled (password correct)!")
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
                pendingGroup = Group.objects.get(name='PendingUsers')
                pendingGroup.user_set.add(user)
                context = RequestContext(request, {'registrationStatus':
                    "Registration successful!"})

    return render(request, 'login/register.html', context)
