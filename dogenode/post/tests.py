from django.test import TestCase
from author.models import Author
from comments.models import Comment
from post.models import Post, AuthorPost
from author.models import Author

from django.contrib.auth.models import User


class PostTestCase(TestCase):
    
    def setUp(self):
        """
        Creating 2 authors, 3 posts. author1 gets 1 post, author 2 gets 2 posts
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
        self.assertIsNotNone(post,
                            "Post does not exist")
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
