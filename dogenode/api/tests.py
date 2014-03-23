from django.test import TestCase

from django.contrib.auth.models import User

from author.models import Author, Relationship
from post.models import Post, AuthorPost
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser


import json

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

        userid1 = User.objects.get(username="utestuser1").id
        userid2 = User.objects.get(username="utestuser2").id
        userid3 = User.objects.get(username="utestuser3").id

        response1 = self.client.post(
                        '/api/friends/%s/%s' % (userid1, userid2),
                        content_type="application/json")
        response2 = self.client.post(
                        '/api/friends/%s/%s' % (userid2, userid1),
                        content_type="application/json")
        response3 = self.client.post(
                        '/api/friends/%s/%s' % (userid2, userid3),
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
                               "friends":[userid2, userid3]})

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

        self.assertEqual(json.loads(response.content),
                      {"status":"success",
                       "message":
                           "You are now following %s" % user6.username})

        # test the same thing, there should be no change
        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
                      {"status":"success",
                       "message":
                           "Already following %s, no change" % user6.username})

        # utestuser6 befriends utestuser5
        friendRequestData["author"]["id"] = user6.id
        friendRequestData["friend"]["author"]["id"] = user5.id

        response = self.client.post('/api/friendrequest',
                                     content_type="application/json",
                                     data=json.dumps(friendRequestData))

        self.assertEqual(json.loads(response.content),
                      {"status":"success",
                       "message":
                           "You are now friends with %s" % user5.username})

    def testRESTfriends(self):

        userid1 = User.objects.get(username="utestuser1").id
        userid2 = User.objects.get(username="utestuser2").id
        userid3 = User.objects.get(username="utestuser3").id
        userid4 = User.objects.get(username="utestuser4").id

        # 2 friends
        response1 = self.client.post('/api/friends/%s' % userid3,
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':userid3,
                                      'authors': [userid1, userid2,
                                                  userid3, userid4]}))

        # 1 friend
        response2 = self.client.post('/api/friends/%s' % userid3,
                     content_type="application/json",
                     data=json.dumps({'query':"friends",
                                      'author':userid3,
                                      'authors': [userid1, userid2,
                                                  userid3]}))

        # no friends
        response3 = self.client.post('/api/friends/%s' % userid3,
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

        self.assertEqual(json.loads(response1.content),
                              {"query":"friends",
                               "author":userid3,
                               "friends":[userid2, userid4]})
        self.assertEqual(json.loads(response2.content),
                              {"query":"friends",
                               "author":userid3,
                               "friends":[userid2]})
        self.assertEqual(json.loads(response3.content),
                              {"query":"friends",
                               "author":userid3,
                               "friends":[]})
        self.assertEqual(json.loads(response4.content,
                         object_hook=_decode_dict),
                              {"query":"friends",
                               "author":0,

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

