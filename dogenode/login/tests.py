from django.test import TestCase
from login.models import Author

# Create your tests here.
class AuthorTestCase(TestCase):
    def setUp(self):
        Author.objects.create(username="unittestuser", password="testpassword")

    def test_get_password_from_username(self):
        user = Author.objects.get(username="unittestuser")
        self.assertEqual(user.getPassword(), "testpassword")
