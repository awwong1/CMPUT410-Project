from django.test import TestCase

from author.models import Author
from django.contrib.auth.models import User

# Create your tests here.
class AuthorTestCase(TestCase):
    def setUp(self):
        User.objects.create_user(username="utestuser", password="testpassword")

    # Test that Author is connected to User properly
    def testGetAcceptedStatus(self):
        user = User.objects.get(username="utestuser")
        self.assertEqual(len(Author.objects.filter(user=user)), 1)

        author = Author.objects.get(user=user)
        self.assertEqual(author.accepted, False)

