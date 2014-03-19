from django.test import TestCase

from django.contrib.auth.models import User

from author.models import Author, Relationship

import json

# Create your tests here.
class RESTfulTestCase(TestCase):

    def setUp(self):

        user1 = User.objects.create_user(username="utestuser1",
                                         password="testpassword")
        user2 = User.objects.create_user(username="utestuser2",
                                         password="password")
        user3 = User.objects.create_user(username="utestuser3",
                                         password="password")
        user4 = User.objects.create_user(username="utestuser4",
                                         password="password")
        user5 = User.objects.create_user(username="utestuser5",
                                         password="testpassword")
        user6 = User.objects.create_user(username="utestuser6",
                                         password="testpassword")

        author1, _ = Author.objects.get_or_create(user=user1)
        author2, _ = Author.objects.get_or_create(user=user2)
        author3, _ = Author.objects.get_or_create(user=user3)
        author4, _ = Author.objects.get_or_create(user=user4)
        author5, _ = Author.objects.get_or_create(user=user5)
        author6, _ = Author.objects.get_or_create(user=user6)

        # author1 follows author2
        Relationship.objects.get_or_create(author1=author1,
                                           author2=author2,
                                           relationship=False)
        # author1 follows author3
        Relationship.objects.get_or_create(author1=author1,
                                           author2=author3,
                                           relationship=False)
        # author2 is friends with author3
        Relationship.objects.get_or_create(author1=author2,
                                           author2=author3,
                                           relationship=True)

        # author3 is friends with author4
        Relationship.objects.get_or_create(author1=author3,
                                           author2=author4,
                                           relationship=True)

    def testRESTrelationships(self):

        user5 = User.objects.get(username="utestuser5")
        user6 = User.objects.get(username="utestuser6")

        # utestuser5 sends friend request to utestuser6
        friendRequestData = {
                "query":"friendrequest",
                "author":{
                    "id": user5.id,
                    "host":"http://127.0.0.1:5454/",
                    "displayname":"utestuser1"
                },
                "friend":{
                    "author":{
                        "id": user6.id,
                        "host":"http://127.0.0.1:5454/",
                        "displayname":"utestuser2",
                        "url":"http://127.0.0.1:5454/author/utestuser2"
                    }
                }
        }

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertItemsEqual(json.loads(response.content),
                          {"status":"success",
                           "message":"You are now following %s" % user6.id})

        # test the same thing, there should be no change
        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertItemsEqual(json.loads(response.content),
                          {"status":"success",
                           "message":
                               "Already following %s, no change" % user6.id})

        # utestuser6 befriends utestuser5
        friendRequestData["author"]["id"] = user6.id
        friendRequestData["friend"]["author"]["id"] = user5.id

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertItemsEqual(json.loads(response.content),
                      {"status":"success",
                       "message":"You are now friends with %s" % user5.id})

    def testRESTfriends(self):

        userid1 = User.objects.get(username="utestuser1").id
        userid2 = User.objects.get(username="utestuser2").id
        userid3 = User.objects.get(username="utestuser3").id
        userid4 = User.objects.get(username="utestuser4").id

        # 2 friends
        response1 = self.client.post('/api/friends/utestuser3',
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':userid3,
                                      'authors': [userid1, userid2,
                                                  userid3, userid4]}))

        # 1 friend
        response2 = self.client.post('/api/friends/utestuser3',
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':userid3,
                                      'authors': [userid1, userid2,
                                                  userid3]}))

        # no friends
        response3 = self.client.post('/api/friends/utestuser3',
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':userid3,
                                      'authors': [userid1]}))

        # user doesn't exist
        response4 = self.client.post('/api/friends/0',
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':0,
                                      'authors': [userid1, userid2,
                                                  userid3, userid4]}))

        self.assertItemsEqual(json.loads(response1.content),
                              {"query":"friends",
                               "author":userid3,
                               "friends":[userid2, userid4]})
        self.assertItemsEqual(json.loads(response2.content),
                              {"query":"friends",
                               "author":userid3,
                               "friends":[userid2]})
        self.assertItemsEqual(json.loads(response3.content),
                              {"query":"friends",
                               "author":userid3,
                               "friends":[]})
        self.assertItemsEqual(json.loads(response4.content),
                              {"query":"friends",
                               "author":0,
                               "friends":[]})
