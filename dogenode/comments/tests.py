from django.test import TestCase
from author.models import Author
from comments.models import Comment
from post.models import Post

from django.contrib.auth.models import User

# Create your tests here.
class CommentTestCase(TestCase):
    def setUp(self):
        User.objects.create_user(username="utestuser", password="testpassword")
        user = User.objects.get(username="utestuser")
        author, _ = Author.objects.get_or_create(user=user)
        Post.objects.create(author=author, content="This post...")
        post = Post.objects.get(content="This post...")
        Comment.objects.create(
            comment_auth=author,
            post_ref=post,
            comment_text="So spice!")
    
    def testCommentTextExists(self):
        self.assertEqual(
            len(Comment.objects.filter(comment_text="So spice!")), 1)

    def testCommentAuthExists(self):
        user = User.objects.get(username="utestuser")
        author = Author.objects.get(user=user)
        self.assertEqual(
            len(Comment.objects.filter(comment_auth=author)), 1)

    def testCommentPostRef(self):
        post = Post.objects.get(content="This post...")
        self.assertEqual(
            len(Comment.objects.filter(post_ref=post)), 1)
