from django.test import TestCase
from author.models import Author
from comments.models import Comment
from post.models import Post, AuthorPost
from author.models import Author

from django.contrib.auth.models import User

import json

class PostTestCase(TestCase):

    def setUp(self):
        """
        Creating 2 authors, 3 posts. author1 gets 1 post, author 2 gets 2 posts
        Sets up base url for REST tests
        """
        User.objects.create_user(username="mockuser1", password="mockpassword")
        user1 = User.objects.get(username="mockuser1")
        author1, _ = Author.objects.get_or_create(user=user1)

        User.objects.create_user(username="mockuser2", password="mockpassword")
        user2 = User.objects.get(username="mockuser2")
        author2, _ = Author.objects.get_or_create(user=user2)

        post1 = Post.objects.create(title="title1",
                                    description="desc1",
                                    content="post1",
                                    visibility=Post.PUBLIC) 
        post2 = Post.objects.create(title="title2",
                                    description="desc2",
                                    content="post2", 
                                    visibility=Post.PUBLIC) 
        post3 = Post.objects.create(title="title3",
                                    description="desc3",
                                    content="post3",
                                    visibility=Post.PRIVATE) 

        AuthorPost.objects.create(post=post1, author=author1)
        AuthorPost.objects.create(post=post2, author=author2)
        AuthorPost.objects.create(post=post3, author=author2)

    def testGetPostByTitle(self):
        """
        Tests if you can get a post by title and verifies if all of its
        fields are correct.
        """
        post = Post.objects.filter(title="title1")[0]
        self.assertIsNotNone(post, "Post does not exist")
        self.assertEquals(post.title, "title1", 
                            "Title does not match")
        self.assertEquals(post.content, "post1", 
                            "Content does not match")
        self.assertEquals(post.description, "desc1", 
                            "Description does not match")
        self.assertEquals(post.visibility, Post.PUBLIC, 
                            "Visibility does not match")

    def testGetAllPosts(self):
        """
        Tests if you can get all existsing posts
        """
        posts = Post.objects.filter()
        self.assertEquals(len(posts), 3,  
                            "Created 3 Posts, found " + str(len(posts)))
        for post in posts:
            self.assertIsNotNone(post, "Post is None")

    def testGetAllAuthorPosts(self):
        """
        Tests if you can get all of an author's posts
        """
        user = User.objects.get(username="mockuser2")
        author = Author.objects.get(user=user)
        posts = AuthorPost.objects.filter(author=author)

        self.assertEquals(len(posts), 2, 
                            "mockuser2 had 2 posts, found " + str(len(posts)))
    
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
        post4 = Post.objects.create(title="title4",
                                    description="desc4",
                                    content="post4",
                                    visibility=Post.PUBLIC) 
        
        post = Post.objects.filter(title="title4")[0]
        self.assertIsNotNone(post, "Post should exist!")
        post4.delete()
        post = Post.objects.filter(title="title4")
        self.assertEquals(len(post), 0, "Post should not exist")


    def testViewsAddPost(self):
        """
        Test if you can create a post via add_post in views
        """
        self.client.login(username="mockuser1", password="mockpassword")

        url = "/posts/add_post/"

        response = self.client.post(url, 
                                    {'title':'title6',
                                     'description':'desc6',
                                     'content':'content6',
                                     'visibility':Post.PUBLIC,
                                     'visibilityExceptions':'',
                                     'categories':'',
                                     'contentType': Post.PLAIN},
                                    HTTP_REFERER='/author/stream.html')
        self.assertEqual(response.status_code, 302, 
                        "Post creation was not successful, code:" + 
                         str(response.status_code))
        post = Post.objects.get(title="title6")
        self.assertIsNotNone(post, "Post was not successfully created")
        post.delete()

    def testViewsGetPost(self):
        """
        Gets a single post using the post function in post/views.py.
        """
        post = Post.objects.filter(title="title1")[0]
        post_id = post.id
        
        self.client.login(username="mockuser1", password="mockpassword")
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
        post4 = Post.objects.create(title="title4",
                                    description="desc4",
                                    content="post4",
                                    visibility=Post.PUBLIC) 
        
        user = User.objects.get(username="mockuser1")
        author = Author.objects.get(user=user)
        AuthorPost.objects.create(post=post4, author=author)

        post = Post.objects.filter(title="title4")[0]
        self.assertIsNotNone(post, "Post should exist!")

        post_id = post.id

        self.client.login(username="mockuser1", password="mockpassword")
        url = "/posts/delete_post/"

        response = self.client.post(url, {'post_id': post_id})

        self.assertEqual(response.status_code, 302, 
                        "Post deletion not successful, code: " + 
                        str(response.status_code))

        posts = Post.objects.filter(title="title4");
        self.assertEquals(len(posts), 0, "Post was not successfully deleted")

    def testViewsGetNonExistantPost(self):
        """
        Tests trying to retrieve an non existant post. Right now,
        if error DoesNotExist pops up, it's coming from the post/views.py
        file, and should be what is generated.
        """
        self.client.login(username="mockuser1", password="mockpassword")

        url = "/posts/999/"
        try:
            response = self.client.get(url, HTTP_ACCEPT='text/html')
            self.assertFalse(True, "This post should not exist")
        except Post.DoesNotExist as e:
            self.assertTrue(True)        
        
    
    def testRESTAddUpdatePost(self):
        """
        Test if you can add and update a post via PUT request with /post/postid
        """
        self.client.login(username="mockuser1", password="mockpassword")

        url = "/posts/add_post/"

        response = self.client.post(url, 
                                    {'title':'title6',
                                     'description':'desc6',
                                     'content':'content6',
                                     'visibility':Post.PUBLIC,
                                     'visibilityExceptions':'',
                                     'categories':'',
                                     'contentType': Post.PLAIN},
                                    HTTP_REFERER='/author/stream.html')
        self.assertEqual(response.status_code, 302, 
                        "Post creation was not successful, code:" + 
                         str(response.status_code))
        post = Post.objects.get(title="title6")
        self.assertIsNotNone(post, "Post was not successfully created")
        post.delete()

    def testRESTGetPost(self):
        """
        Gets a single post via a GET and a POST request for /post/postid
        Tests:
        1. GET an existing post
        2. POST an exisiting post
        3. GET a non existing post
        4. POST a non existing post
        """
        post = Post.objects.filter(title="title1")[0]
        post_id = post.id
        
        self.client.login(username="mockuser1", password="mockpassword")
        url = "/posts/" + str(post_id) + "/"

        response = self.client.get(url, HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, 200, 
                        "Post should exist, but response was not 200")
        self.assertTemplateUsed(response, 'fragments/post_content.html',
                                "Wrong template(s) returned")
	self.assertIsNotNone(response.context['posts'][0])


    def testRESTGetAllPublicPosts(self):
        """
        Tests retreiving all public posts on the server. Sends a GET / POST
        request to /posts/
        """
        pass

