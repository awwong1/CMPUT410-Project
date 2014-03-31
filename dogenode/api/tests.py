from django.test import TestCase

from django.contrib.auth.models import User

from author.models import (Author, RemoteAuthor,
                           LocalRelationship, RemoteRelationship)
from post.models import Post, AuthorPost
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser


import json, uuid

# TODO: generate this automatically
OURHOST = "http://127.0.0.1:8000/"

# The decoding functions are from
# http://stackoverflow.com/a/6633651
def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):

    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv

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

        remoteAuthor1, _ = RemoteAuthor.objects.get_or_create(
                            displayName="remoteAuthor1",
                            host="http://127.0.0.1:8001/",
                            url="http://127.0.0.1:8001/author/remoteAuthor1")

        remoteAuthor2, _ = RemoteAuthor.objects.get_or_create(
                            displayName="remoteAuthor2",
                            host="http://127.0.0.1:8001/",
                            url="http://127.0.0.1:8001/author/remoteAuthor2")

        # author1 follows author2
        LocalRelationship.objects.get_or_create(author1=author1,
                                           author2=author2,
                                           relationship=False)
        # author1 follows author3
        LocalRelationship.objects.get_or_create(author1=author1,
                                           author2=author3,
                                           relationship=False)
        # author2 is friends with author3
        LocalRelationship.objects.get_or_create(author1=author2,
                                           author2=author3,
                                           relationship=True)

        # author2 follows remoteAuthor1
        RemoteRelationship.objects.get_or_create(localAuthor=author2,
                                           remoteAuthor=remoteAuthor1,
                                           relationship=0)

        # author3 is friends with author4
        LocalRelationship.objects.get_or_create(author1=author3,
                                           author2=author4,
                                           relationship=True)

        # author3 is friends with remoteAuthor1
        RemoteRelationship.objects.get_or_create(localAuthor=author3,
                                           remoteAuthor=remoteAuthor1,
                                           relationship=2)

        # remoteAuthor2 follows author2
        RemoteRelationship.objects.get_or_create(localAuthor=author2,
                                           remoteAuthor=remoteAuthor2,
                                           relationship=1)

        # creating some posts for authors
        post1 = Post.objects.create(content="content1",
                                    title="title1",
                                    visibility=Post.PUBLIC)
        post2 = Post.objects.create(content="content2",
                                    title="title2",
                                    visibility=Post.PRIVATE)
        post3 = Post.objects.create(content="content3",
                                    title="title3",
                                    visibility=Post.PRIVATE)
        post4 = Post.objects.create(content="content4",
                                    title="title4",
                                    visibility=Post.FRIENDS)
        post5 = Post.objects.create(content="content5",
                                    title="title5",
                                    visibility=Post.FOAF)
        post6 = Post.objects.create(content="content6",
                                    title="title6",
                                   visibility=Post.PUBLIC)
        post7 = Post.objects.create(content="content7",
                                    title="title7",
                                    visibility=Post.PRIVATE)
        post8 = Post.objects.create(content="content8",
                                    title="title8",
                                    visibility=Post.SERVERONLY)
        
        # Author1 should see post 1, post 2, post 6, post 8
        AuthorPost.objects.create(post=post1, author=author1)
        AuthorPost.objects.create(post=post2, author=author1)
        AuthorPost.objects.create(post=post3, author=author2)
        AuthorPost.objects.create(post=post4, author=author2)
        AuthorPost.objects.create(post=post5, author=author2)
        AuthorPost.objects.create(post=post6, author=author2)
        AuthorPost.objects.create(post=post7, author=author3)
        AuthorPost.objects.create(post=post8, author=author3)


    def testRESTareFriends(self):

        user1 = User.objects.get(username="utestuser1")
        user2 = User.objects.get(username="utestuser2")
        user3 = User.objects.get(username="utestuser3")

        author1, _ = Author.objects.get_or_create(user=user1)
        author2, _ = Author.objects.get_or_create(user=user2)
        author3, _ = Author.objects.get_or_create(user=user3)

        remoteAuthor1, _ = RemoteAuthor.objects.get_or_create(
                                displayName="remoteAuthor1")
        remoteAuthor2, _ = RemoteAuthor.objects.get_or_create(
                                displayName="remoteAuthor2")

        response1 = self.client.post(
                        '/api/friends/%s/%s' % (author1.guid, author2.guid),
                        content_type="application/json")
        response2 = self.client.post(
                        '/api/friends/%s/%s' % (author2.guid, author1.guid),
                        content_type="application/json")
        response3 = self.client.post(
                        '/api/friends/%s/%s' % (author2.guid, author3.guid),
                        content_type="application/json")

        response4 = self.client.post(
                    '/api/friends/%s/%s' % (author3.guid, remoteAuthor1.guid),
                    content_type="application/json")
        response5 = self.client.post(
                    '/api/friends/%s/%s' % (remoteAuthor1.guid, author3.guid),
                    content_type="application/json")
        response6 = self.client.post(
                    '/api/friends/%s/%s' % (author2.guid, remoteAuthor2.guid),
                    content_type="application/json")

        self.assertEqual(json.loads(response1.content),
                              {"query":"friends",
                               "friends":"NO"})
        self.assertEqual(json.loads(response2.content),
                              {"query":"friends",
                               "friends":"NO"})
        self.assertEqual(json.loads(response3.content,
                         object_hook=_decode_dict),
                              {"query":"friends",
                               "friends":[author2.guid, author3.guid]})

        self.assertEqual(json.loads(response4.content,
                         object_hook=_decode_dict),
                              {"query":"friends",
                               "friends":[author3.guid, remoteAuthor1.guid]})
        self.assertEqual(json.loads(response5.content,
                         object_hook=_decode_dict),
                              {"query":"friends",
                               "friends":[remoteAuthor1.guid, author3.guid]})
        self.assertEqual(json.loads(response6.content,
                         object_hook=_decode_dict),
                              {"query":"friends",
                               "friends":"NO"})

    def testRESTrelationships(self):

        # test local friend requests

        user5 = User.objects.get(username="utestuser5")
        user6 = User.objects.get(username="utestuser6")

        author5, _ = Author.objects.get_or_create(user=user5)
        author6, _ = Author.objects.get_or_create(user=user6)

        # utestuser5 sends friend request to utestuser6
        friendRequestData = {
                "query":"friendrequest",
                "author":{
                    "id": author5.guid,
                    "host": OURHOST,
                    "displayname":"utestuser1"
                },
                "friend":{
                    "author":{
                        "id": author6.guid,
                        "host": OURHOST,
                        "displayname":"utestuser2",
                        "url":"http://127.0.0.1:5454/author/utestuser2"
                    }
                }
        }

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
                      {"status":"success",
                       "message":
                           "You are now following %s" % user6.username})

        localRelationship = LocalRelationship.objects.filter(
                                author1=author5,
                                author2=author6,
                                relationship=False)

        self.assertEqual(len(localRelationship), 1)

        # test the same thing, there should be no change
        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
                      {"status":"success",
                       "message":
                           "Already following %s, no change" % user6.username})

        localRelationship = LocalRelationship.objects.filter(
                                author1=author5,
                                author2=author6,
                                relationship=False)

        self.assertEqual(len(localRelationship), 1)

        # utestuser6 befriends utestuser5
        friendRequestData["author"]["id"] = author6.guid
        friendRequestData["friend"]["author"]["id"] = author5.guid

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
                      {"status":"success",
                       "message":
                           "You are now friends with %s" % user5.username})

        localRelationship = LocalRelationship.objects.filter(
                                author1=author5,
                                author2=author6,
                                relationship=True)

        self.assertEqual(len(localRelationship), 1)


        # test remote friend requests

        #TODO: current specs do not include url as part of the post request
        remoteUser1 = {"id": str(uuid.uuid4()),
                       "host": "http://127.0.0.1:8001/",
                       "url": "http://127.0.0.1:8001/author/remoteUser1",
                       "displayname": "remoteUser1"}

        # remoteUser1 sends a friend request to utestuser5

        friendRequestData["author"] = remoteUser1.copy()

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
                      {"status":"success",
                       "message":
                           "You are now following %s" % user5.username})

        remoteAuthor1 = RemoteAuthor.objects.filter(
                                guid=remoteUser1["id"],
                                host=remoteUser1["host"],
                                url=remoteUser1["url"],
                                displayName=remoteUser1["displayname"])

        self.assertEqual(len(remoteAuthor1), 1)

        remoteAuthor1 = remoteAuthor1[0]

        remoteRelationship = RemoteRelationship.objects.filter(
                                localAuthor=author5,
                                remoteAuthor=remoteAuthor1,
                                relationship=1)

        self.assertEqual(len(remoteRelationship), 1)

        # utestuser6 sends a friend request to remoteUser1

        friendRequestData["author"]["id"] = author6.guid
        friendRequestData["author"]["host"] = OURHOST

        remoteUser1["url"] = "%sauthor/%s" % (remoteUser1["host"],
                                              remoteUser1["id"])

        friendRequestData["friend"]["author"] = remoteUser1.copy()

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
                  {"status":"success",
                   "message":
                       "You are now following %s" % remoteUser1["displayname"]})

        remoteRelationship = RemoteRelationship.objects.filter(
                                localAuthor=author6,
                                remoteAuthor=remoteAuthor1,
                                relationship=0)

        self.assertEqual(len(remoteRelationship), 1)

        # utestuser5 befriends remoteUser1

        friendRequestData["author"]["id"] = author5.guid

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
              {"status":"success",
               "message":
                   "You are now friends with %s" % remoteUser1["displayname"]})

        remoteRelationship = RemoteRelationship.objects.filter(
                                localAuthor=author5,
                                remoteAuthor=remoteAuthor1,
                                relationship=2)

        self.assertEqual(len(remoteRelationship), 1)

    def testRESTfriends(self):

        user1 = User.objects.get(username="utestuser1")
        user2 = User.objects.get(username="utestuser2")
        user3 = User.objects.get(username="utestuser3")
        user4 = User.objects.get(username="utestuser4")

        author1, _ = Author.objects.get_or_create(user=user1)
        author2, _ = Author.objects.get_or_create(user=user2)
        author3, _ = Author.objects.get_or_create(user=user3)
        author4, _ = Author.objects.get_or_create(user=user4)

        remoteAuthor1, _ = RemoteAuthor.objects.get_or_create(
                            displayName="remoteAuthor1")

        author1guid = str(author1.guid)
        author2guid = str(author2.guid)
        author3guid = str(author3.guid)
        author4guid = str(author4.guid)

        remoteAuthor1guid = str(remoteAuthor1.guid)

        # 3 friends
        response1 = self.client.post('/api/friends/%s' % author3guid,
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':author3guid,
                                      'authors': [author1guid, author2guid,
                                                  author3guid, author4guid,
                                                  remoteAuthor1guid]}))

        # 1 friend
        response2 = self.client.post('/api/friends/%s' % author3guid,
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':author3guid,
                                      'authors': [author1guid, author2guid,
                                                  author3guid]}))

        # no friends
        response3 = self.client.post('/api/friends/%s' % author3guid,
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':author3guid,
                                      'authors': [author1guid]}))

        # user doesn't exist
        response4 = self.client.post('/api/friends/0',
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':0,
                                      'authors': [author1guid, author2guid,
                                                  author3guid, author4guid]}))

        #TODO: sometimes this test fails because the friends aren't returned
        # in the same order. This is a failure of the test not the view

        self.assertEqual(json.loads(response1.content,
                                    object_hook=_decode_dict),
                              {"query":"friends",
                               "author":author3guid,
                               "friends":[author2guid, author4guid,
                                          remoteAuthor1guid]})
        self.assertEqual(json.loads(response2.content,
                                    object_hook=_decode_dict),
                              {"query":"friends",
                               "author":author3guid,
                               "friends":[author2guid]})
        self.assertEqual(json.loads(response3.content,
                                    object_hook=_decode_dict),
                              {"query":"friends",
                               "author":author3guid,
                               "friends":[]})
        self.assertEqual(json.loads(response4.content,
                                    object_hook=_decode_dict),
                              {"query":"friends",
                               "author":"0",
                               "friends":[]})

    def testRESTGetAllAuthorPosts(self):
        """
        Tests getting all the posts of an author that are visible by user
        making the request. Sends a GET request to /author/authorid/posts.
        utestuser1 made post 1 and post 2, so those two posts should be 
        retrieved.
        """
        # Authenicate and send a get request 
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)
        self.client.login(username="utestuser1", password="testpassword")

        response = self.client.get('/api/author/%s/posts/' % author.guid,
                                    HTTP_ACCEPT = 'application/json')
        
        # Response code check
        self.assertEqual(response.status_code, 200)
       
        # Author should have 2 posts
        posts = json.loads(response.content, object_hook=_decode_dict)
        self.assertEqual(len(posts['posts']), 2, 
                         "%s should have 2 posts!" % "utestuser1")

        # Make sure they are the same!
        for i in range(len(posts['posts'])):
            post = posts["posts"][i]
            self.assertEquals(post["author"]["displayName"], "utestuser1",
                              "This is not the %s's post!" % "utestuser1")  
            if post["title"] == "title2":
                epost = Post.objects.get(title="title2")
            elif post["title"] == "title1":
                epost = Post.objects.get(title="title1")

            postAuthor = AuthorPost.objects.get(post=epost).author
            expectedPost = {
                            'guid': epost.guid,
                            'title': epost.title, 
                            'description': epost.description, 
                            'content': epost.content, 
                            'visibility': epost.visibility, 
                            'contentType': epost.contentType, 
                            'origin': epost.origin, 
                            'author': {'url': postAuthor.url, 
                                       'host': postAuthor.host, 
                                       'displayName': postAuthor.user.username, 
                                       'id': postAuthor.guid}, 
                            'comments': [],
                            'categories': [], 
                            }

            for key in expectedPost.keys():
                self.assertEquals(expectedPost[key], post[key])


    def testRESTStream(self):
        """
        Tests retrieving all posts that are visible to the current user.
        Sends a GET request to /author/posts/
        utestuser1 shouserialize ld be able to see post 1, 2, 6, and 8
        """
        # Authenicate and send a get request 
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)
        self.client.login(username="utestuser1", password="testpassword")

        response = self.client.get('/api/author/posts/', 
                                    HTTP_ACCEPT = 'application/json')
        
        # Response code check
        self.assertEqual(response.status_code, 200)

        # Author should have 2 posts
        posts = json.loads(response.content, object_hook=_decode_dict)
        self.assertEqual(len(posts['posts']), 4, 
                         "%s should see 4 posts!" % "utestuser1")

