from django.test import TestCase
from author.models import Author
from comments.models import Comment
from post.models import Post

from django.contrib.auth.models import User


# Create your tests here.
class PostTestCase(TestCase):
    
    def setUp(self):
        User.objects.create_user(username="mockuser", password="mockpassword")
        user = User.objects.get(username="mockuser")
        author, _ = Author.objects.get_or_create(user=user)
        Post.objects.create(author=author, content="This is a post") 

    def testFieldsExists(self):
        user = User.objects.get(username="mockuser")
        author = Author.objects.get(user=user)
        post = Post.objects.filter()[0]
        self.assertIsNotNone(post)
        self.assertEquals(post.author, author)
        self.assertEquals(post.content, "This is a post")
