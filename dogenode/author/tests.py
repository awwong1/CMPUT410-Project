from django.test import TestCase

from post.models import Post, AuthorPost
from author.models import Author, LocalRelationship
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import json
import uuid

# Create your tests here.
class AuthorTestCase(TestCase):
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

        noGithubUser = User.objects.create_user(username="nogithubuser",
                                         password="testpassword")
        githubUser = User.objects.create_user(username="githubuser",
                                         password="testpassword")

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)
        author4 = Author.objects.get(user=user4)
        author5 = Author.objects.get(user=user5)

        noGithubAuthor = Author.objects.get(user=noGithubUser)
        githubAuthor = Author.objects.get(user=githubUser)

        githubAuthor.githubUsername = "ajyong"
        githubAuthor.save()

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

        # author3 is friends with author4
        LocalRelationship.objects.get_or_create(author1=author3,
                                           author2=author4,
                                           relationship=True)

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

        # author is accepted by default after registering
        author = Author.objects.get(user=user)
        self.assertEqual(author.accepted, True)

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

        self.assertEqual(author1.getFriends(), {"local":[], "remote":[]})
        self.assertEqual(author1.getPendingSentRequests(),
                         {"local": [author2, author3], "remote":[]})
        self.assertEqual(author1.getPendingReceivedRequests(),
                         {"local": [], "remote": []})

        self.assertEqual(author2.getFriends(),
                         {"local": [author3], "remote":[]})
        self.assertEqual(author2.getPendingSentRequests(),
                         {"local":[], "remote":[]})
        self.assertEqual(author2.getPendingReceivedRequests(),
                         {"local": [author1], "remote": []})

        self.assertItemsEqual(author3.getFriends(),
                              {"local": [author2, author4], "remote":[]})
        self.assertEqual(author3.getPendingSentRequests(),
                         {"local": [], "remote": []})
        self.assertEqual(author3.getPendingReceivedRequests(),
                         {"local": [author1], "remote": []})

        self.assertTrue(author2.isFriendOfAFriend(author4))
        self.assertTrue(author4.isFriendOfAFriend(author2))
        self.assertFalse(author2.isFriendOfAFriend(author3))
        self.assertFalse(author1.isFriendOfAFriend(author2))
        self.assertFalse(author2.isFriendOfAFriend(author1))


    def testViewsGetProfile(self):
        """
        Tests retrieving the profile of an author
        """
        self.client.login(username="utestuser1", password="testpassword")
        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)

        url = "/author/" + str(author1.guid) + "/"
        response = self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "author/profile.html")
        self.assertEquals(response.context['firstName'], "")
        self.assertEquals(response.context['lastName'], "")
        self.assertEquals(response.context['username'], "utestuser1")
        self.assertEquals(response.context['userIsAuthor'], True)


    def testViewsEditProfile(self):
        """
        Tests editing the profile of an author
        """
        self.client.login(username="utestuser5", password="testpassword")
        
        url =  "/author/edit_profile/"
        body = {'firstName':'bob1',
                'lastName':'bob2',
                'oldPassword':'testpassword',
                'newPassword':'bob3',
                'githubUsername':''}
        response = self.client.post(url, body)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "author/edit_profile.html")
        
        # TODO XXX: check password correctly changed?
        user5 = User.objects.get(username="utestuser5")
        self.assertEquals(user5.first_name, "bob1")
        self.assertEquals(user5.last_name, "bob2")


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
        self.assertEquals(len(response.context['posts']), 3)
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
        self.assertEquals(response.context['results'][0]["displayname"],
                          "utestuser2")
        self.assertEquals(response.context['results'][0]["relationship"],
                          "Following")

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

        url = "/author/"+str(author1.guid)+"/posts/"

        response = self.client.get(url, HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'post/posts.html',
                                "Wrong template(s) returned")
        self.assertEquals(len(response.context['posts']), 2)

    def testNoGithubEvents(self):
        """
        Given a new user that has no posts and no GitHub username associated
        with it, we should not be expecting the stream to have any posts.
        """

        self.client.login(username="nogithubuser", password="testpassword")
        user = User.objects.get(username="nogithubuser")
        author = Author.objects.get(user=user)

        response = self.client.get("/author/stream/", HTTP_ACCEPT='text/html')

        postIds = AuthorPost.objects.filter(author=author)

        self.assertEqual(len(postIds), 0, "Posts were found")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "author/stream.html")
        self.assertEqual(len(response.context["posts"]), 0,
                         "Post count not zero")

    def testOnlyGithubEvents(self):
        """
        Given a new user that has no posts but has a GitHub username associated
        with it, we should only be expecting GitHub posts in the stream.
        """

        self.client.login(username="githubuser", password="testpassword")
        user = User.objects.get(username="githubuser")
        author = Author.objects.get(user=user)

        self.assertEqual(author.githubUsername, "ajyong",
                         "GitHub username not equal to setup")

        response = self.client.get("/author/stream/", HTTP_ACCEPT="text/html")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "author/stream.html")
        self.assertGreater(len(response.context["posts"]), 0,
                           "No GitHub posts were sent to the client")

        for t in response.context["posts"]:
            self.assertTrue(t[0]["title"].startswith("GitHub"),
                            "Post title does not start with GitHub")
