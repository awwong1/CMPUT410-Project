from django.test import TestCase

from comments.models import Comment
from post.models import Post, AuthorPost, PostVisibilityException
from author.models import Author, LocalRelationship

from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import collections

import json
import uuid

class PostTestCase(TestCase):

    def setUp(self):
        """
        Creating 2 authors, 3 posts. author1 gets 1 post, author 2 gets 2 posts
        Sets up base url for REST tests
        """
        # User and AUthor setup
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

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)
        author4 = Author.objects.get(user=user4)
        author5 = Author.objects.get(user=user5)

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

        # Post Set up
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

    def testGetPostByTitle(self):
        """
        Tests if you can get a post by title and verifies if all of its
        fields are correct.
        """
        post = Post.objects.filter(title="title1")[0]
        self.assertIsNotNone(post, "Post does not exist")
        self.assertEquals(post.title, "title1", 
                            "Title does not match")
        self.assertEquals(post.content, "content1", 
                            "Content does not match")
        self.assertEquals(post.visibility, Post.PUBLIC, 
                            "Visibility does not match")

    def testGetAllPosts(self):
        """
        Tests if you can get all existsing posts
        """
        posts = Post.objects.all()
        self.assertEquals(len(posts), 9,  
                            "Created 9 Posts, found " + str(len(posts)))
        for post in posts:
            self.assertIsNotNone(post, "Post is None")

    def testGetAllAuthorPosts(self):
        """
        Tests if you can get all of an author's posts
        """
        user = User.objects.get(username="utestuser2")
        author = Author.objects.get(user=user)
        posts = AuthorPost.objects.filter(author=author)

        self.assertEquals(len(posts), 4, 
                            "utestuser2 had 4 posts, found " + str(len(posts)))

    def testPostisAllowedToViewPost(self):
        """
        Tests post model function isAllowedToViewPost
        """
        titles = ["title1", "title2", "title3", "title4", "title5", 
                  "title6", "title7", "title8", "title9"]
        posts = [Post.objects.get(title=t) for t in titles]

        # User1 testing
        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        for i in range(len(posts)):
            visCheck = posts[i].isAllowedToViewPost(author1, True)
            # Auth1 should get their own PUBLIC and PRIVATE post (1, 2)
            # Auth1 follows Auth2, should get their PUBLIC post (post6)
            # Auth1 is on a visibility exception of post9 (PRIVATE of Auth3)
            if i in [0, 1, 5, 8]:
                self.assertEqual(visCheck, True)
            else:
                self.assertEqual(visCheck, False) 

        # Auth3 is Friends with Auth2, should get FRIENDS, FOAF and PUBLIC
        user3 = User.objects.get(username="utestuser3")
        author3 = Author.objects.get(user=user3)
        for i in range(len(posts)):
            visCheck = posts[i].isAllowedToViewPost(author3, True)
            # Auth3 is friends with Auth2, should get their FRI, FOAF, PUB 
            # posts (posts 4, 5, 6)
            # Auth3 should get their own posts (posts 7, 8, 9)
            if i in [3, 4, 5, 6, 7, 8]:
                self.assertEqual(visCheck, True)
            else:
                self.assertEqual(visCheck, False) 

        # Auth4 is friends with Auth3, who is friends with Auth2, should
        # get post5. Also should get Auth3's SERVONLY since they are friends
        user4 = User.objects.get(username="utestuser4")
        author4 = Author.objects.get(user=user4)
        for i in range(len(posts)):
            visCheck = posts[i].isAllowedToViewPost(author4, True)
            # Auth4 is should get Auth2's FOAF (post5) and Auth3's SERONLY (7)
            if i in [4, 7]:
                self.assertEqual(visCheck, True)
            else:
                self.assertEqual(visCheck, False) 

    def testGetNonExistantPost(self):
        """
        Tests if you can get a non-existant post
        """
        posts = Post.objects.filter(title="IDoNotExist")
        self.assertEquals(len(posts), 0, "Post should not exist!")

    def testDeletePost(self):
        """
        Tests if you can delete a post
        """
        newPost = Post.objects.create(title="newPost!",
                                    description="new",
                                    content="new content here!",
                                    visibility=Post.PUBLIC) 
        
        post = Post.objects.filter(title="newPost!")[0]
        self.assertIsNotNone(post, "Post should exist!")
        post.delete()
        post2 = Post.objects.filter(title="newPost!")
        self.assertEquals(len(post2), 0, "Post should not exist")

    def testViewsGetPost(self):
        """
        Gets a single post using the post function in post/views.py.
        """
        post = Post.objects.filter(title="title1")[0]
        post_id = post.guid
        
        self.client.login(username="utestuser1", password="testpassword")
        url = "/posts/" + str(post_id) + "/"

        response = self.client.get(url, HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, 200, 
                        "Post should exist, but response was not 200")
        self.assertTemplateUsed(response, 'fragments/post_content.html',
                                "Wrong template(s) returned")
        self.assertIsNotNone(response.context['posts'][0])

    def testViewsDeletePost(self):
        """
        Tests deleting a post. First creates a new post, then deletes it.
        """
        newPost = Post.objects.create(title="newPost!",
                                    description="new",
                                    content="new content here!",
                                    visibility=Post.PUBLIC) 
        
        user = User.objects.get(username="utestuser1")
        author = Author.objects.get(user=user)
        AuthorPost.objects.create(post=newPost, author=author)

        post = Post.objects.filter(title="newPost!")[0]
        self.assertIsNotNone(post, "Post should exist!")

        post_id = post.guid

        self.client.login(username="utestuser1", password="testpassword")
        url = "/posts/delete_post/"

        response = self.client.post(url, {'post_id': post_id})

        self.assertEqual(response.status_code, 302, 
                        "Post deletion not successful, code: " + 
                        str(response.status_code))

        posts = Post.objects.filter(title="newPost!");
        self.assertEquals(len(posts), 0, "Post was not successfully deleted")

    def testViewsGetNonExistantPost(self):
        """
        Tests trying to retrieve an non existant post. Right now,
        if error DoesNotExist pops up, it's coming from the post/views.py
        file, and should be what is generated.
        """
        self.client.login(username="utestuser1", password="testpassword")

        url = "/posts/" + str(uuid.uuid4()) + "/"
        try:
            response = self.client.get(url, HTTP_ACCEPT='text/html')
            self.assertFalse(True, "This post should not exist")
        except Post.DoesNotExist as e:
            self.assertTrue(True)
    

    def testViewsGetAllPublicPosts(self):
        """
        Tests retreiving all public posts on the server. Sends a GET / POST
        request to /posts/
        """
        self.client.login(username="utestuser1", password="testpassword")
        response = self.client.get('/posts/', HTTP_ACCEPT='text/html')

        # Two posts should be public: post1, and post2
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'post/public_posts.html')
        self.assertIsNotNone(response.context['posts'])
        self.assertEqual(len(response.context['posts']), 2)
 
