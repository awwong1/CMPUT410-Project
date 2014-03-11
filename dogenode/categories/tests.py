from django.test import TestCase

from categories.models import Category
from author.models import Author, Relationship
from post.models import Post, PostCategory, AuthorPost
from django.contrib.auth.models import User

import json

class CategoryTestCase(TestCase):
    def setUp(self):
        Category.objects.create(name="one")
        Category.objects.create(name="two")
        Category.objects.create(name="three")

        user1 = User.objects.create_user(username="user1",
                                         password="password")
        user2 = User.objects.create_user(username="user2",
                                         password="password")
        user3 = User.objects.create_user(username="user3",
                                         password="password")
        user4 = User.objects.create_user(username="user4",
                                         password="password")

        author1, _ = Author.objects.get_or_create(user=user1)
        author2, _ = Author.objects.get_or_create(user=user2)
        author3, _ = Author.objects.get_or_create(user=user3)
        author4, _ = Author.objects.get_or_create(user=user4)

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
        # TODO
        pass

    def testGetPostsWithCategory(self):
        # TODO
        pass
