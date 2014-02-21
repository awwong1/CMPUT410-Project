from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from login.models import Author

# Create your views here.
def index(request):
    context = None

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = Author.objects.filter(username=username)

        if len(user) == 0:
            return HttpResponse("No user named %s was found" % username)
        elif user[0].password != password:
            return HttpResponse("Password '%s' is incorrect" % password)
        else:
            return HttpResponse("Login successful!")

    return render(request, 'login/index.html', context)
