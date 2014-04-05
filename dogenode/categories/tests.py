from django.test import TestCase

from categories.models import Category
from author.models import Author, LocalRelationship
from post.models import Post, PostCategory, AuthorPost
from django.contrib.auth.models import User

import json
import uuid

class CategoryTestCase(TestCase):
    def setUp(self):
        cat1 = Category.objects.create(name="one")
        cat2 = Category.objects.create(name="two")
        cat3 = Category.objects.create(name="three")

        # Shamelessly copying these from author/tests.py
        user1 = User.objects.create_user(username="user1",
                                         password="password")
        user2 = User.objects.create_user(username="user2",
                                         password="password")
        user3 = User.objects.create_user(username="user3",
                                         password="password")
        user4 = User.objects.create_user(username="user4",
                                         password="password")

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)
        author4 = Author.objects.get(user=user4)

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

        # Author2 should see posts 1, 3, 4, 5, 6, 8
        AuthorPost.objects.create(post=post3, author=author2)
        AuthorPost.objects.create(post=post4, author=author2)
        AuthorPost.objects.create(post=post5, author=author2)
        AuthorPost.objects.create(post=post6, author=author2)

        # Author3 should see posts 1, 4, 5, 6, 7, 8
        AuthorPost.objects.create(post=post7, author=author3)
        AuthorPost.objects.create(post=post8, author=author3)

        # Author4 should see posts 1, 5, 6, 8

        # post 1 has all 3 categories
        PostCategory.objects.create(post=post1, category=cat1)
        PostCategory.objects.create(post=post1, category=cat2)
        PostCategory.objects.create(post=post1, category=cat3)

        PostCategory.objects.create(post=post2, category=cat1)

        PostCategory.objects.create(post=post3, category=cat2)

        PostCategory.objects.create(post=post4, category=cat3)

        PostCategory.objects.create(post=post5, category=cat2)

        PostCategory.objects.create(post=post6, category=cat3)

        PostCategory.objects.create(post=post7, category=cat1)
        PostCategory.objects.create(post=post7, category=cat3)


    # Test the RESTful API by POSTing a category, and accept JSON back.
    def testAddCategoryJson(self):
        name = "new"
        response = self.client.post('/categories/add', {'name': name},
                                    HTTP_ACCEPT='application/json')
        self.assertEqual('application/json', response['Content-Type'])

        responseContent = json.loads(response.content)
        self.assertEqual(responseContent['message'],
                         "%s added to Dogenode!" % name,
                         ("Response message not what was expected.: %s" %
                            responseContent['message']))
        self.assertTrue(responseContent['id'] > 0,
                        "ID was less than 1: %i" % responseContent['id'])
        self.assertEqual(responseContent['name'], name,
            "Category name is not equal: %s" % responseContent['name'])

    # Same test as above, but accept plaintext back.
    def testAddCategoryPlain(self):
        name = "new"
        response = self.client.post('/categories/add', {'name': name},
                                    HTTP_ACCEPT='text/plain')
        self.assertEqual('text/plain', response['Content-Type'])

        responseContent = response.content.splitlines()
        self.assertEqual(responseContent[0], "%s added to Dogenode!" % name,
                         ("Response message not what was expected.: %s" %
                            responseContent[0]))
        self.assertIn("id: ", responseContent[1],
                      "ID field was not returned: %s" % responseContent[1])
        self.assertEqual(responseContent[2], "name: %s" % name,
            "Category name is not equal: %s" % responseContent[2])

    def testAddExistingCategoryJson(self):
        name = "one"
        response = self.client.post('/categories/add', {'name': name},
                                    HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 409, "409 not returned")
        self.assertEqual('application/json', response['Content-Type'])

        responseContent = json.loads(response.content)
        self.assertEqual(responseContent['message'],
                         "%s already exists!" % name,
                         ("Response message not what was expected.: %s" %
                            responseContent['message']))
        self.assertTrue(responseContent['id'] > 0,
                        "ID was less than 1: %i" % responseContent['id'])
        self.assertEqual(responseContent['name'], name,
            "Category name is not equal: %s" % responseContent['name'])

    def testAddExistingCategoryPlain(self):
        name = "one"
        response = self.client.post('/categories/add', {'name': name},
                                    HTTP_ACCEPT='text/plain')
        self.assertEqual(response.status_code, 409, "409 not returned")
        self.assertEqual('text/plain', response['Content-Type'])

        responseContent = response.content.splitlines()
        self.assertEqual(responseContent[0], "%s already exists!" % name,
                         ("Response message not what was expected.: %s" %
                            responseContent[0]))
        self.assertIn("id: ", responseContent[1],
                      "ID field was not returned: %s" % responseContent[1])
        self.assertEqual(responseContent[2], "name: %s" % name,
            "Category name is not equal: %s" % responseContent[2])

    def testAddEmptyCategoryJson(self):
        name = ""
        response = self.client.post('/categories/add', {'name': name},
                                    HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400, "400 not returned")
        self.assertEqual('application/json', response['Content-Type'])

        responseContent = json.loads(response.content)
        self.assertEqual(responseContent['message'],
                         "A name is required.",
                         ("Response message not what was expected: %s" %
                            responseContent['message']))
        self.assertEqual(responseContent['id'], -1,
                         "ID not equal to -1: %s" % responseContent['id'])
        self.assertEqual(responseContent['name'], "",
                         "Category name is not empty: %s" % responseContent['name'])

    def testAddEmptyCategoryPlain(self):
        name = ""
        response = self.client.post('/categories/add', {'name': name},
                                    HTTP_ACCEPT='text/plain')
        self.assertEqual(response.status_code, 400, "400 not returned")
        self.assertEqual('text/plain', response['Content-Type'])

        responseContent = response.content.splitlines()
        self.assertEqual(responseContent[0], "A name is required.",
                         ("Response message not what was expected.: %s" %
                            responseContent[0]))
        self.assertIn("id: ", responseContent[1],
                      "ID field was not returned: %s" % responseContent[1])
        self.assertEqual(responseContent[2], "name: ",
            "Category name is not empty: %s" % responseContent[2])

    def testGetCategories(self):
        response = self.client.get('/categories/',
                                   HTTP_ACCEPT='application/json')
        responseContent = json.loads(response.content)

        self.assertEquals(len(responseContent), 3)

    def testGetPostsWithCategoryOne(self):
        """
        For all authors, test what they should be getting back when they
        request all viewable posts with category "one".
        """
        cat1 = Category.objects.get(name="one")

        user1 = User.objects.get(username="user1")
        user2 = User.objects.get(username="user2")
        user3 = User.objects.get(username="user3")
        user4 = User.objects.get(username="user4")

        author1 = Author.objects.get(user=user1)
        author2 = Author.objects.get(user=user2)
        author3 = Author.objects.get(user=user3)
        author4 = Author.objects.get(user=user4)

        for (u, a) in zip((user1, user2, user3, user4),
                          (author1, author2, author3, author4)):
            self.client.login(username=u, password="password")
            response = self.client.get("/categories/%d/" % cat1.id,
                                       HTTP_ACCEPT="application/json")

            responseContent = json.loads(response.content)
            allAllowedPosts = Post.getAllowedPosts(a)
            postIds = PostCategory.objects.filter(post__in=allAllowedPosts,
                                                  category=cat1).values_list(
                                                    'post', flat=True)
            postsWithCategory = Post.objects.filter(id__in=postIds)

            for post in postsWithCategory:
                self.assertTrue(post.as_dict() in responseContent,
                                "A category one post that was supposed to be " \
                                "viewable was not found")

            self.client.logout()
