from django.test import TestCase

from author.models import Author, Relationship
from django.contrib.auth.models import User

# Create your tests here.
class AuthorRelationshipsTestCase(TestCase):
    def setUp(self):
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
