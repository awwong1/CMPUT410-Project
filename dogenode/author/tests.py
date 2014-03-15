from django.test import TestCase

from post.models import Post, AuthorPost
from author.models import Author, Relationship
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import json
import yaml

# Create your tests here.
class AuthorRelationshipsTestCase(TestCase):
    def setUp(self):

        user1 = User.objects.create_user(username="utestuser1",
                                         password="testpassword")
        user2 = User.objects.create_user(username="utestuser2",
                                         password="password")
        user3 = User.objects.create_user(username="utestuser3",
                                         password="password")
        user4 = User.objects.create_user(username="utestuser4",
                                         password="password")

        author1, _ = Author.objects.get_or_create(user=user1)
        author2, _ = Author.objects.get_or_create(user=user2)
        author3, _ = Author.objects.get_or_create(user=user3)
        author4, _ = Author.objects.get_or_create(user=user4)

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
        
    # Test that Author is connected to User properly
    def testGetAcceptedStatus(self):
        user = User.objects.get(username="utestuser1")
        self.assertEqual(len(Author.objects.filter(user=user)), 1)

        author = Author.objects.get(user=user)
        self.assertEqual(author.accepted, False)

    # Test that following, unfollowing, befriending, unfriending work
    def testRelationships(self):
        user1 = User.objects.get(username="utestuser1")
        user2 = User.objects.get(username="utestuser2")
        user3 = User.objects.get(username="utestuser3")
        user4 = User.objects.get(username="utestuser4")

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)
        author4 = Author.objects.get(user=user4)

        self.assertItemsEqual(author1.getFriends(), [])
        self.assertItemsEqual(author1.getPendingSentRequests(),
                              [author2, author3])
        self.assertItemsEqual(author1.getPendingReceivedRequests(), [])

        self.assertItemsEqual(author2.getFriends(), [author3])
        self.assertItemsEqual(author2.getPendingSentRequests(), [])
        self.assertEqual(author2.getPendingReceivedRequests(), [author1])

        self.assertItemsEqual(author3.getFriends(), [author2, author4])
        self.assertItemsEqual(author3.getPendingSentRequests(), [])
        self.assertEqual(author3.getPendingReceivedRequests(), [author1])

        self.assertTrue(author2.isFriendOfAFriend(author4))
        self.assertTrue(author4.isFriendOfAFriend(author2))
        self.assertFalse(author2.isFriendOfAFriend(author3))
        self.assertFalse(author1.isFriendOfAFriend(author2))
        self.assertFalse(author2.isFriendOfAFriend(author1))

    # TODO: I'm not sure the posts are sending data using JSON
    def testRESTfriends(self):

        # 2 friends
        response1 = self.client.post('/author/friends/utestuser3',
                     data={'query':"friends",
                           'author':"utestuser3",
                           'authors': ["utestuser1", "utestuser2",
                                       "utestuser3", "utestuser4"]})

        # 1 friend
        response2 = self.client.post('/author/friends/utestuser3',
                     data={'query':"friends",
                           'author':"utestuser3",
                           'authors': ["utestuser1", "utestuser2",
                                       "utestuser3"]})

        # no friends
        response3 = self.client.post('/author/friends/utestuser3',
                     data={'query':"friends",
                           'author':"utestuser3",
                           'authors': ["utestuser1"]})

        # user doesn't exist
        response4 = self.client.post('/author/friends/unosuchuser',
                     data={'query':"friends",
                           'author':"unosuchuser",
                           'authors': ["utestuser1", "utestuser2",
                                       "utestuser3", "utestuser4"]})

        self.assertItemsEqual(json.loads(response1.content),
                              {"query":"friends",
                               "author":"utestuser3",
                               "friends":["utestuser2", "utestuser4"]})
        self.assertItemsEqual(json.loads(response2.content),
                              {"query":"friends",
                               "author":"utestuser3",
                               "friends":["utestuser2"]})
        self.assertItemsEqual(json.loads(response3.content),
                              {"query":"friends",
                               "author":"utestuser3",
                               "friends":[]})
        self.assertItemsEqual(json.loads(response4.content),
                              {"query":"friends",
                               "author":"unosuchuser",
                               "friends":[]})

    def testViewsGetProfile(self):
        """
        Tests retrieving the profile of an author

        TODO xxx: update test once author model has been refactored
        """
        self.client.login(username="utestuser1", password="testpassword")
        
        url = "/author/profile/utestuser1/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "author/profile.html")
        self.assertEquals(response.context['firstName'], "")
        self.assertEquals(response.context['lastName'], "")
        self.assertEquals(response.context['username'], "utestuser1")
        self.assertEquals(response.context['aboutMe'], "")
        self.assertEquals(response.context['userIsAuthor'], True)


    def testViewsEditProfile(self):
        """
        Tests editing the profile of an author

        TODO XXX: update test once author model has been refactored,
        and this should be done with a PUT not a POST
        """
        user5 = User.objects.create_user(username="utestuser5",
                                         password="testpassword")
        author5 = Author.objects.create(user=user5)
        
        self.client.login(username="utestuser5", password="testpassword")
        
        url =  "/author/edit_profile/"
        body = {'firstName':'bob1',
                'lastName':'bob2',
                'oldPassword':'testpassword',
                'newPassword':'bob3',
                'aboutMe':'bob4'}
        response = self.client.post(url, body)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "author/edit_profile.html")
        # TODO: This test has to be a loooottt better. But for now....
        # also, not sure how to test to make sure password has changed
        user5 = User.objects.get(username="utestuser5")
        author5 = Author.objects.get(user=user5)
        self.assertEquals(user5.first_name, "bob1")
        self.assertEquals(user5.last_name, "bob2")
        self.assertEquals(author5.about_me, "bob4")
        author5.delete()
        user5.delete()


    def testStream(self):
        """
        Tests retrieving the stream of an author

        utestuser1 should be able to see post 1, 2, 6, and 8
        """
        self.client.login(username="utestuser1", password="testpassword")
        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        
        url = "/author/stream/"
        response = self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.context['posts']), 4)	
        self.assertTemplateUsed(response, "author/stream.html")

        titles = ["title1", "title2", "title6", "title8"]
        for post in response.context['posts']:
            self.assertIn(str(post[0].title), titles)

    def testSearch(self):
        """
        Tests searching for an author.
        """
        # Made two new users, was getting wierd error using others
        self.client.login(username="utestuser1", password="testpassword")

        url = "/author/search_results/"

        # searching for an exisiting user
        response = self.client.post(url, data={'username': "utestuser2"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEquals(response.context['searchphrase'], "utestuser2")
        self.assertEquals(response.context['results'][0][0], "utestuser2")
        self.assertEquals(response.context['results'][0][1], "Following")

       # searching for a non existing user 
        response = self.client.post(url, data={'username': "nouser"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEquals(response.context['searchphrase'], "nouser")
        self.assertEquals(len(response.context['results']), 0)

    def testViewsGetAllAuthorPosts(self):
        """
        Tests getting all the posts of an author using the posts function
        in post/views.py. utestuser1 made post 1 and post 2, so those two
        posts should be retrieved.
        """        
        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        self.client.login(username="utestuser1", password="testpassword")

        url = "/author/"+str(author1.id)+"/posts/"

        response = self.client.get(url, HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'post/posts.html',
                                "Wrong template(s) returned")
        self.assertEquals(len(response.context['posts']), 2)

    def testRESTGetAllAuthorPosts(self):
        """
        Tests getting all the posts of an author that are visible by user
        making the request. Sends a GET request to /author/authorid/posts.
        utestuser1 made post 1 and post 2, so those two posts should be 
        retrieved.
        """        
        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        
        self.client.login(username="utestuser1", password="testpassword")

        url = "/author/"+str(author1.id)+"/posts/"

        response = self.client.get(url, HTTP_ACCEPT='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        posts = yaml.load(response.content)

        self.assertEqual(len(posts['posts']), 2)
       
        titles = ["title1", "title2"] 
        for post in posts['posts']:
            # self.assertEquals(post["author"][])  TODO: FIX ONCE AUTHOR MODEL DONE
            self.assertIn(post["title"], titles)
      
    def testRESTStream(self):
        """
        Tests retrieving all posts that are visible to the current user.
        Sends a GET request to /author/posts/
        utestuser1 should be able to see post 1, 2, 6, and 8
        """
        
        self.client.login(username="utestuser1", password="testpassword")
        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        
        url = "/author/stream/"
        response = self.client.get(url, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        posts = yaml.load(response.content)
        self.assertEquals(len(posts["posts"]), 4)	

        titles = ["title1", "title2", "title6", "title8"]
        for post in posts["posts"]:
            self.assertIn(post["title"], titles)
