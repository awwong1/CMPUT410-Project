from django.test import TestCase
from author.models import Author
from comments.models import Comment
from post.models import Post

from django.contrib.auth.models import User

import uuid


# Create your tests here.
class CommentTestCase(TestCase):
    
    def setUp(self):
        User.objects.create_user(username="mockuser1", password="mockpassword")
        user1 = User.objects.get(username="mockuser1")
        author1, _ = Author.objects.get_or_create(user=user1)

        post1 = Post.objects.create(
                            guid=uuid.uuid4(),
                            title="title1",
                            description="desc1",
                            content="post1",
                            visibility=Post.PUBLIC)

        post2 = Post.objects.create(
                            guid=uuid.uuid4(),
                            title="title2",
                            description="desc2",
                            content="post2",
                            visibility=Post.PUBLIC)
           
        Comment.objects.create(
                author=author1,
                post_ref=post1,
                comment="comment1")
        
        Comment.objects.create(
                author=author1,
                post_ref=post1,
                comment="comment2")
        
        Comment.objects.create(
                author=author1,
                post_ref=post2,
                comment="comment3")

    def testGetComment(self):
        """
        Gets a single comment by the comment content.
        """
        comment = Comment.objects.get(comment="comment1")
        self.assertIsNotNone(comment, 
                     "Comment exists, but was not found")

        user1 = User.objects.get(username="mockuser1")
        author1 = Author.objects.get(user=user1)
        post1 = Post.objects.filter(title="title1")[0]
    
        self.assertEquals(comment.author, author1, "Author id does not match")
        self.assertEquals(comment.post_ref, post1, "Post id does not match")
        self.assertEquals(comment.comment, "comment1", 
                  "Comment (content) does not match")
        self.assertIsNotNone(comment.pub_date)

    def testGetAllComments(self):
        """
        Tests getting all comments in the database
        """
        comments = Comment.objects.filter()
        self.assertEqual(len(comments), 3, "3 Comments exist" + 
                 "but only " +  str(len(comments)) + " found")

    def testGetAllPostComments(self):
        """
        Tests retrieving all comments of a post from the database
        """
        post2 = Post.objects.filter(title="title2")[0]
            
        comments = Comment.objects.filter(post_ref=post2)
        self.assertEqual(len(comments), 1, "Post has one comment," + 
                 "but " +  str(len(comments)) + " were found")

    def testGetNonExistantComment(self):
        """
        Tests retrieving a non existant comment from the database
        """
        comments = Comment.objects.filter(comment="idontexist")
        self.assertEquals(len(comments), 0, "Comment should not exist!")


    def testDeleteComment(self):
        """
        Tests comment deletion from database
        """
        post1 = Post.objects.filter(title="title1")[0]
        user1 = User.objects.get(username="mockuser1")
        author1= Author.objects.get(user=user1)

        Comment.objects.create(
                author=author1,
                post_ref=post1,
                comment="comment4")
        
        
        comment = Comment.objects.get(comment="comment4")
        self.assertIsNotNone(comment, 
                     "Comment exists, but was not found")

        comment.delete()
        self.assertEquals(len(Comment.objects.filter(comment="comment4")),
                  0, "Comment was not properly deleted")

    def testViewsGetPostComments(self):
        """
        Tests getting all comments of a post using the get_post_comments
        in coments/views.py
        """
        self.client.login(username="mockuser1", password="mockpassword")
        post1_id = Post.objects.filter(title="title1")[0].guid
        
        url = "/comments/" + str(post1_id) + "/"
        
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200,
                 "Was unable to retrieve comments of post, code: " +
                 str(response.status_code))
        self.assertTemplateUsed(response, 'fragments/post_content.html',
                    "Wrong template returned")
        print(response)

    def testViewsAddComment(self):
        """
        Tests if you can add a comment via add_comment in comments/views.py
        """    
        self.client.login(username="mockuser1", password="mockpassword")
        url = "/comments/add_comment/"
        post1_id = Post.objects.filter(title="title1")[0].guid
        
        response = self.client.post(url,
                        {'post_id':post1_id,
                         'newComment':'comment5'},
                         HTTP_REFERER='/author/stream.html')
        self.assertEqual(response.status_code, 302,
                 "Comment creation was not succesful, code: " +
                 str(response.status_code))
        comment = Comment.objects.filter(comment="comment5")[0]
        self.assertIsNotNone(comment, "Comment was not succesfully created")    

    def testViewsRemoveComment(self):
        """
        Tests if you can delete a comment via remove_comment in 
        comments/views.py
        """    
        self.client.login(username="mockuser1", password="mockpassword")
        
        post1 = Post.objects.filter(title="title1")[0]
        user1 = User.objects.get(username="mockuser1")
        author1= Author.objects.get(user=user1)

        Comment.objects.create(
                author=author1,
                post_ref=post1,
                comment="comment6")
        
        self.assertNotEqual(len(Comment.objects.filter(comment="comment6")), 0)

        comment_id = Comment.objects.get(comment="comment6").id
        
        url = "/comments/remove_comment/" + str(comment_id) + "/"
        response = self.client.delete(url, 
                          HTTP_REFERER='/author/stream.html')
        self.assertEqual(response.status_code, 302,
                 "Comment deletion was not succesful, code: " +
                 str(response.status_code))
        comments = Comment.objects.filter(comment="comment6")
        self.assertEqual(len(comments), 0, 
                        "Comment was not succesfully deleted")    


