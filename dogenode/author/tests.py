from django.test import TestCase

from author.models import Author, Relationship
from django.contrib.auth.models import User

import json

BASE_URL = "http://testserver"

# Create your tests here.
class AuthorRelationshipsTestCase(TestCase):
    def setUp(self, base_url=BASE_URL):
	self.base_url=base_url

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
	

	url = self.base_url + "/author/profile/utestuser1/"
	response = self.client.get(url)
	self.assertEqual(response.status_code, 200)
	self.assertTemplateUsed(response, "author/profile.html")
	# TODO: This test has to be a loooottt better. But for now....
	self.assertContains(response, "utestuser1")	


    def testViewsEditProfile(self):
        """
	Tests editing the profile of an author

	TODO XXX: update test once author model has been refactored,
	and this should be done with a PUT not a POST
	"""
	user5 = User.objects.create_user(username="utestuser5",
                                         password="testpassword")
        author5, _ = Author.objects.get_or_create(user=user5)
	
	self.client.login(username="utestuser5", password="testpassword")
	
	url = self.base_url + "/author/edit_profile/"
	body = {'firstName':'bob1',
		'lastName':'bob2',
		'oldPassword':'testpassword',
		'newPassword':'bob3',
		'aboutMe':'bob4'}
	response = self.client.post(url, body)
	
	self.assertEqual(response.status_code, 200)
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

	TODO xxx: update test once author model has been refactored,
	might want to test to make sure posts that shouldn't be 
	visible aren't...
	"""
	self.client.login(username="utestuser1", password="testpassword")

	url = self.base_url + "/author/stream/"
	response = self.client.get(url)
	self.assertEqual(response.status_code, 200)
	self.assertTemplateUsed(response, "author/stream.html")
	
	# TODO: Should test a lot more...currently not sure how to do so
	# and will also probably have to parse html if its not json
	

    def testSearch(self):
	"""
	Tests searching for an author.
	"""
	# Made two new users, was getting wierd error using others
	user5 = User.objects.create_user(username="utestuser5",
                                         password="testpassword")
        Author.objects.get_or_create(user=user5)
	
	user6 = User.objects.create_user(username="utestuser6",
                                         password="testpassword")
        Author.objects.get_or_create(user=user6)
        
	self.client.login(username="utestuser5", password="testpassword")
	
	url = self.base_url + "/author/search_results/"

        response = self.client.post(url,
                     data={'username': "utestuser6"})

	self.assertEqual(response.status_code, 200)

	# Find a better way to test this...  
	self.assertContains(response, "utestuser6")
	user5.delete()
	user6.delete()      
