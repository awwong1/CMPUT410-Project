from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q

from django.contrib.auth.models import User

from author.models import Author, Relationship

import json

# Create your views here.

def areFriends(request, userid1, userid2):

    response = {"query":"friends",
                "friends":"NO"}

    if request.method == 'POST':

        user1 = User.objects.filter(id=userid1)
        user2 = User.objects.filter(id=userid2)

        if len(user1) > 0 and len(user2) > 0:

            author1, _ = Author.objects.get_or_create(user=user1[0])
            author2, _ = Author.objects.get_or_create(user=user2[0])

            if author2 in author1.getFriends():
                response["friends"] = [int(userid1), int(userid2)]

    return HttpResponse(json.dumps(response),
                        content_type="application/json")

# The POST request is sent to a url which includes the user ID, but the user
# ID is also sent in the POST request body.
# Right now I am using the user ID sent in the request body
def getFriendsFromList(request, userid):

    # check if userid is actually an int first
    if userid.isdigit():

        response = {"query":"friends",
                    "author":int(userid),
                    "friends":[]}

        if request.method == 'POST':

            jsonData = json.loads(request.body)

            userid = jsonData['author']
            user = User.objects.filter(id=userid)

            if len(user) > 0:

                author, _ = Author.objects.get_or_create(user=user)

                friendUserids = [a.user.id for a in author.getFriends()]
                
                friends = list(set(friendUserids) & set(jsonData["authors"]))
                
                response["author"] = userid
                response["friends"] = friends

    else:

        response = {"query":"friends",
                    "author":userid,
                    "friends":[]}


    return HttpResponse(json.dumps(response),
                        content_type="application/json")

def sendFriendRequest(request):

    response = {"status":"failure", "message":"Internal failure"}

    if request.method == 'POST':

        jsonData = json.loads(request.body)

        userid1 = jsonData["author"]["id"]
        userid2 = jsonData["friend"]["author"]["id"]

        user1 = User.objects.filter(id=userid1)
        user2 = User.objects.filter(id=userid2)

        if len(user1) > 0 and len(user2) > 0:

            user1 = user1[0]
            user2 = user2[0]

            author1, _ = Author.objects.get_or_create(user=user1)
            author2, _ = Author.objects.get_or_create(user=user2)
            
            relationship = Relationship.objects.filter(
                                ((Q(author1=author1) & Q(author2=author2))
                                |(Q(author2=author1) & Q(author1=author2))))

            if len(relationship) > 0:

                relationship = relationship[0]

                # author1 already follows author2, no change
                if relationship.author1 == author1:
                    response["status"] = "success"
                    response["message"] = ("Already following %s, no change" %
                                            user2.username)
                # author2 follows author1, so now make them friends
                else:
                    relationship.relationship = True
                    relationship.save()
                    response["status"] = "success"
                    response["message"] = ("You are now friends with %s" %
                                            user2.username)
            else:
                # author1 will follow author2
                _, _ = Relationship.objects.get_or_create(
                                                   author1=author1,
                                                   author2=author2,
                                                   relationship=False)
                response["status"] = "success"
                response["message"] = ("You are now following %s" %
                                            user2.username)

    return HttpResponse(json.dumps(response),
                        content_type="application/json")
        
