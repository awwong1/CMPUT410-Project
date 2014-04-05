from django.test import TestCase

from django.contrib.auth.models import User

from author.models import (Author, RemoteAuthor,
                           LocalRelationship, RemoteRelationship)
from post.models import Post, PostVisibilityException, AuthorPost

from api.views import OURHOST

import urllib
import json, uuid

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

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)
        author4 = Author.objects.get(user=user4)
        author5 = Author.objects.get(user=user5)
        author6 = Author.objects.get(user=user6)

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
        post1 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content1",
                                    title="title1",
                                    visibility=Post.PUBLIC)
        post2 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content2",
                                    title="title2",
                                    visibility=Post.PRIVATE)
        post3 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content3",
                                    title="title3",
                                    visibility=Post.PRIVATE)
        post4 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content4",
                                    title="title4",
                                    visibility=Post.FRIENDS)
        post5 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content5",
                                    title="title5",
                                    visibility=Post.FOAF)
        post6 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content6",
                                    title="title6",
                                    visibility=Post.PUBLIC)
        post7 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content7",
                                    title="title7",
                                    visibility=Post.PRIVATE)
        post8 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content8",
                                    title="title8",
                                    visibility=Post.SERVERONLY)
        post9 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content9",
                                    title="title9",
                                    visibility=Post.PRIVATE)

        # Author1 should see post 1, post 2, post 6, post 8
        AuthorPost.objects.create(post=post1, author=author1)
        AuthorPost.objects.create(post=post2, author=author1)
        AuthorPost.objects.create(post=post3, author=author2)
        AuthorPost.objects.create(post=post4, author=author2)
        AuthorPost.objects.create(post=post5, author=author2)
        AuthorPost.objects.create(post=post6, author=author2)
        AuthorPost.objects.create(post=post7, author=author3)
        AuthorPost.objects.create(post=post8, author=author3)
        AuthorPost.objects.create(post=post9, author=author3)

        # Author1 should be able to view post9 too
        PostVisibilityException.objects.create(post=post9, author=author1)

    def testRESTfriends(self):

        user5 = User.objects.create_user(username="utestuser5",
                                         password="testpassword")

        author5 = Author.objects.get(user=user5)

        response1 = self.client.post('/api/search/query=user5',
                                     content_type="application/json")

        self.assertEqual(json.loads(response1.content,
                                    object_hook=_decode_dict),
            [{"url": "%sauthor/profile/%s" % (OURHOST, str(author5.guid)),
              "host": OURHOST,
              "displayname": user5.username,
              "id": author5.guid}])


    def testRESTareFriends(self):

        user1 = User.objects.get(username="utestuser1")
        user2 = User.objects.get(username="utestuser2")
        user3 = User.objects.get(username="utestuser3")

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)

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

        author5 = Author.objects.get(user=user5)
        author6 = Author.objects.get(user=user6)

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

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)
        author4 = Author.objects.get(user=user4)

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

        # This next 2 asserts are required because assertItemsEqual only
        # checks the keys, and assertItemsEqual fails if the lists contain
        # the same values but are in different orders. Aaaaargh.
        jsonResponse1 = json.loads(response1.content, object_hook=_decode_dict)

        self.assertItemsEqual(jsonResponse1,
                                  {"query":"friends",
                                   "author":author3guid,
                                   "friends":[author2guid, author4guid,
                                              remoteAuthor1guid]})
        self.assertItemsEqual(jsonResponse1["friends"],
                                   [author2guid, author4guid,
                                    remoteAuthor1guid])

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
        making the request. 
        Sends a GET request to 
            service/author/{AUTHOR_ID}/posts?id={VIEWING_AUTHOR_ID}
        Author2 made multiple posts, but only one of them is public. Since 
        Author2 and Author1 are not friends, only one post should be returned,
        Author2's public post.
        """
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)

        user2 = User.objects.get(username="utestuser2")
        author2 = Author.objects.get(user=user2)

        query = urllib.urlencode({"id":author.guid})
        response = self.client.get('/api/author/%s/posts?%s' % 
                                        (author2.guid, query), 
                                    HTTP_ACCEPT = 'application/json')

        self.assertEqual(response.status_code, 200)
        posts = json.loads(response.content, object_hook=_decode_dict)
        self.assertEqual(len(posts['posts']), 1)
        self.assertEqual(posts["posts"][0]["title"], "title6")
        self.assertEqual(posts["posts"][0]["author"]["id"], author2.guid)

    def testGetPublicPosts(self):
        """
        Tests getting all public posts at:
            api/posts/
        No authentication required.
        """
        response = self.client.get('/api/posts/', 
                                    HTTP_ACCEPT = 'application/json')

        self.assertEqual(response.status_code, 200)

        posts = json.loads(response.content, object_hook=_decode_dict)["posts"]
        self.assertEqual(len(posts), 2, "There should be 2 public posts!")
        for post in posts:
            self.assertEqual(post["visibility"], Post.PUBLIC)

    def testRESTStream(self):
        """
        Tests retrieving all posts that are visible to the local author.
        Sends a GET request to 
            api/author/posts?id={viewingAuthorId}
        utestuser1 should be able to see post 1, 2, 6 and 9
        """
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)

        query = urllib.urlencode({"id":author.guid})
        response = self.client.get('/api/author/posts?%s' % query, 
                                    HTTP_ACCEPT = 'application/json')

        # Response code check
        self.assertEqual(response.status_code, 200)

        posts = json.loads(response.content, object_hook=_decode_dict)
        self.assertEqual(len(posts['posts']), 4)

    def testGetPost(self):
        """
        Gets all the posts with Author1. 
        """
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)
        query = urllib.urlencode({"id":author.guid})

        titles = ["title1", "title2", "title3", "title4", "title5", 
                  "title6", "title7", "title8", "title9"]
        posts = [Post.objects.get(title=t) for t in titles] 
        postIds = [str(p.guid) for p in posts]

        # This is the non-existant post id. With UUIDs, shouldn't generate this
        titles.insert(0, "NoPost")
        postIds.insert(0, "1")

        # Make those requests!
        responses = []
        for i in range(10):
            resp = self.client.get('/api/post/%s?%s' % (postIds[i], query), 
                                    HTTP_ACCEPT = 'application/json')
            responses.append(resp)

        # Should be able to view public and author1's own private post
        # the fourth post had author1 as a visibility exception
        for i in [1, 2, 6, 9]:
            self.assertEqual(responses[i].status_code, 200)
            resp = json.loads(responses[i].content, object_hook=_decode_dict)
            respCont = resp["posts"][0]
            self.assertEqual(titles[i], respCont["title"])

        # Shouldn't be able to view these
        # SERVERONLY - Author1 is on the server but not friends with Author2
        for i in [3, 4, 7, 8]:
            self.assertEqual(responses[i].status_code, 403)

        # And this post doesn't exist
        self.assertEqual(responses[0].status_code, 404)

    def testPutPost(self):
        """
        Tests creating a post and updating said post with PUT
        Deletes the new post when finished.
        """
        # Authenicate and put a new post
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)
        self.client.login(username="utestuser1", password="testpassword")

        query = urllib.urlencode({"id":author.guid})
        newPostId = str(uuid.uuid4())

        # Make a new post with minimum fields required
        newContent = "HI Imma new post!"
        newPostRequestData = { "title":"title", "content":newContent}
        response = self.client.put('/api/post/%s?%s' % (newPostId, query), 
                                    data=json.dumps(newPostRequestData),
                                    content_type = "application/json")

        self.assertEqual(response.status_code, 201)
      
        # Want to get the new post 
        getResponse = self.client.get('/api/post/%s?%s' % (newPostId, query), 
                                    content_type = "application/json",
                                    HTTP_ACCEPT = 'application/json')

        self.assertEqual(getResponse.status_code, 200)
        posts = json.loads(getResponse.content, object_hook=_decode_dict)

        # Some content testing
        self.assertEqual(posts["posts"][0]["guid"], newPostId)
        self.assertEqual(posts["posts"][0]["content"], newContent)
        self.assertEqual(posts["posts"][0]["author"]["id"], author.guid)

        changedContent = "I have changed"
        putResponse = self.client.put('/api/post/%s?%s' % (newPostId, query), 
                                    data=json.dumps({"content":changedContent}),
                                    content_type = "application/json",
                                    HTTP_ACCEPT = 'application/json')

        # The new post's content should not be the old one!
        newPost = Post.objects.get(guid=newPostId)

        self.assertNotEqual(newPost.content, newContent)
        self.assertEqual(newPost.content, changedContent)

        newPost.delete()

    def testRESTauthorProfile(self):
        """
        Gets an author's profile.
        """ 
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)
    
        response = self.client.get('/api/author/%s' % author.guid, 
                                    HTTP_ACCEPT = 'application/json')

        self.assertEqual(response.status_code, 200)             
        authorContent = json.loads(response.content, object_hook=_decode_dict)
        self.assertEqual(authorContent["id"], author.guid)
        self.assertEqual(authorContent["host"], author.host)
        self.assertEqual(authorContent["displayname"], user.username)
        self.assertEqual(authorContent["url"], author.url)

    def testRESTRemoteAuthGetPost(self):
        """
        Get a public post (post 1)
        Get a friends post (post 4)
        Get a private post (post 7)
        Get a serveronly post (post 8)
        """
        user2 = User.objects.get(username="utestuser2")
        author2, _ = Author.objects.get_or_create(user=user2)
        remoteAuthor3, _ = RemoteAuthor.objects.get_or_create(
                            displayName="remoteAuthor3",
                            host="http://127.0.0.1:8001/",
                            url="http://127.0.0.1:8001/author/remoteAuthor3")

        # author2 is friends with remoteAuthor3
        RemoteRelationship.objects.get_or_create(localAuthor=author2,
                                           remoteAuthor=remoteAuthor3,
                                           relationship=2)

        query = urllib.urlencode({"id":remoteAuthor3.guid})
        titles = ["title1", "title4", "title7", "title8"]
        posts = [Post.objects.get(title=t) for t in titles]
        postIds = [str(p.guid) for p in posts]

        responses = []
        # Make those requests!
        for pid in postIds:
            resp = self.client.get('/api/post/%s?%s' % (pid, query), 
                                    HTTP_ACCEPT = 'application/json')
            responses.append(resp)

        # Should be able to view a public and a post where they are frrends
        for i in [0, 1]:
            self.assertEqual(responses[i].status_code, 200)
            resp = json.loads(responses[i].content, object_hook=_decode_dict)
            respCont = resp["posts"][0]
            self.assertEqual(titles[i], respCont["title"])
            self.assertEqual(posts[i].content, respCont["content"])

        # Post 7 is private to another author. Post 8 is server only
        for i in [2, 3]:
            self.assertEqual(responses[i].status_code, 403)

    def testRemoteAuthorGetAllVisiblePosts(self):
        """
        RemoteAuthor3 wants to get all the posts on our node that they can 
        view.
        """
        user2 = User.objects.get(username="utestuser2")
        author2, _ = Author.objects.get_or_create(user=user2)
        remoteAuthor3, _ = RemoteAuthor.objects.get_or_create(
                            displayName="remoteAuthor3",
                            host="http://127.0.0.1:8001/",
                            url="http://127.0.0.1:8001/author/remoteAuthor3")

        # author2 is friends with remoteAuthor3
        RemoteRelationship.objects.get_or_create(localAuthor=author2,
                                           remoteAuthor=remoteAuthor3,
                                           relationship=2)

        query = urllib.urlencode({"id":remoteAuthor3.guid})
        response = self.client.get('/api/author/posts?%s' % query, 
                                    HTTP_ACCEPT = 'application/json')

        # Response code check
        self.assertEqual(response.status_code, 200)
        posts = json.loads(response.content, object_hook=_decode_dict)

        # Two public posts, one friend and one friend of a friend
        self.assertEqual(len(posts['posts']), 4)


    def testRemoteAuthorGetAllLocalAuthorPosts(self):
        """
        Remote author wants to view all of a local author's posts at
            http://service/author/{AUTHOR_ID}/posts?id={VIEWING_AUTHOR_ID}

        RemoteAuthor3 is friends with Author2. Author2 has a public and friends
        post that RemoteAuthor3 can see. RemoteAuthor3 should not be able to
        see Author2's Private post
        TODO: Fix for remote FOAF!
        """
        user2 = User.objects.get(username="utestuser2")
        author2, _ = Author.objects.get_or_create(user=user2)
        remoteAuthor3, _ = RemoteAuthor.objects.get_or_create(
                            displayName="remoteAuthor3",
                            host="http://127.0.0.1:8001/",
                            url="http://127.0.0.1:8001/author/remoteAuthor3")

        # author2 is friends with remoteAuthor3
        RemoteRelationship.objects.get_or_create(localAuthor=author2,
                                           remoteAuthor=remoteAuthor3,
                                           relationship=2)

        query = urllib.urlencode({"id":remoteAuthor3.guid})
        response = self.client.get('/api/author/%s/posts?%s' % 
                                        (author2.guid, query), 
                                    HTTP_ACCEPT = 'application/json')

        self.assertEqual(response.status_code, 200)
        posts = json.loads(response.content, object_hook=_decode_dict)
        # Friend, Public, FOAF of Author2
        self.assertEqual(len(posts['posts']), 3)

        # Make sure they are the same!
        for i in range(len(posts['posts'])):
            post = posts["posts"][i]
            actualPost = Post.objects.get(title=post["title"])
            self.assertEqual(post["title"], actualPost.title)
            self.assertEqual(post["author"]["id"], author2.guid)
