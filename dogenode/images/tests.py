from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase
from django.test.utils import override_settings

from author.models import Author, RemoteAuthor
from images import models as img_models
from post.models import Post, AuthorPost

from PIL import Image
from StringIO import StringIO

import json
import os
import shutil
import urllib
import uuid

# The decoding functions are from
# http://stackoverflow.com/a/6633651
def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):

    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


# Create an isolated test folder in case deletion fails.
@override_settings(MEDIA_ROOT=os.path.abspath(
        os.path.join(settings.BASE_DIR, 'test_media')))
class ImageTestCase(TestCase):

    def setUp(self):
        user1 = User.objects.create_user(username="utestuser1",
                                         password="testpassword")
        author1 = Author.objects.get(user=user1)
        post1 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content1",
                                    title="title1",
                                    visibility=Post.PUBLIC)
        AuthorPost.objects.create(post=post1, author=author1)
        post2 = Post.objects.create(guid=uuid.uuid4(),
                                    content="content2",
                                    title="title2",
                                    visibility=Post.PUBLIC)
        AuthorPost.objects.create(post=post2, author=author1)


        # Testing ImageFields code from: http://janneke-janssen.blogspot.ca/2012/01/django-testing-imagefield-with-test.html
        file_obj = StringIO()
        image = Image.new("RGBA", size=(50,50), color=(255,0,0, 0))
        image.save(file_obj, 'png')
        file_obj.name = 'utestimage1.png'
        file_obj.seek(0)
        cf = ContentFile(file_obj, name="utestimage1.png")
        img1 = img_models.Image.objects.create(author=author1, file=cf,
                                      visibility=img_models.Image.PUBLIC,
                                      contentType="png")
        img_models.ImagePost.objects.create(image=img1, post=post1)

        file_obj.close()

        file_obj = StringIO()
        image = Image.new("RGBA", size=(50,50), color=(0,255,0, 0))
        image.save(file_obj, 'png')
        file_obj.name = 'utestimage2.jpg'
        file_obj.seek(0)
        cf = ContentFile(file_obj, name="utestimage2.jpg")
        img2 = img_models.Image.objects.create(author=author1, file=cf,
                                      visibility=img_models.Image.PUBLIC,
                                      contentType="jpg")
        img_models.ImagePost.objects.create(image=img2, post=post1)

        file_obj.close()

        file_obj = StringIO()
        image = Image.new("RGBA", size=(50,50), color=(0,0,255, 0))
        image.save(file_obj, 'png')
        file_obj.name = 'utestimage3.png'
        file_obj.seek(0)
        cf = ContentFile(file_obj, name="utestimage3.png")
        img3 = img_models.Image.objects.create(author=author1, file=cf,
                                      visibility=img_models.Image.PUBLIC,
                                      contentType="png")
        img_models.ImagePost.objects.create(image=img3, post=post2)

        file_obj.close()

    def tearDown(self):
        # Delete test media folder recursively
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def testSaveGetImage(self):
        """
        Tests saving and retrieving an image to database works
        """
        post2 = Post.objects.get(title="title2")
        img = img_models.ImagePost.objects.filter(post=post2)[0]
        img = img.image
        self.assertIsNotNone(img)
        self.assertIn("utestimage3.png", str(img))
        self.assertEquals(img.visibility, img_models.Image.PUBLIC)

    def testGetPostImages(self):
        """
        Tests getting all the images belonging to a post.
        """
        post1 = Post.objects.get(title="title1")
        imgs = img_models.ImagePost.objects.filter(post=post1)
        self.assertEquals(len(imgs), 2)
        for img in imgs:
            if (("utestimage1" not in str(img))
                and ("utestimage2" not in str(img))):
                self.assertTrue(False, "Incorrect image was retrieved")

    def testUploadImage(self):
        """
        Tests uploading an image.
        """
        file_obj = StringIO()
        image = Image.new("RGBA", size=(100,100), color=(0,255,0,0))
        file_obj.name = 'singlegreenimage.png'
        image.save(file_obj, 'png')
        file_obj.seek(0)

        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        self.client.login(username="utestuser1", password="testpassword")

        imagePostData = {"image": [file_obj]}

        response = self.client.post("/images/upload/", data=imagePostData,
                                    HTTP_ACCEPT="application/json")

        file_obj.close()

        self.assertTrue(response.status_code == 200 or 201,
                         "Single image upload responded as not OK: %d" % response.status_code)

        self.assertTrue(json.loads(response.content), "No content returned")
        self.assertTrue(json.loads(response.content)[0]["name"].endswith(file_obj.name),
                        "Returned file name not the same as the one we gave it")

    def testUploadMultipleImages(self):
        """
        Tests uploading multiple images.
        """
        file_obj = StringIO()
        image = Image.new("RGBA", size=(100,100), color=(0,255,0))
        file_obj.name = 'singlegreenimage.png'
        image.save(file_obj, 'png')
        file_obj.seek(0)

        file_obj2 = StringIO()
        image = Image.new("RGBA", size=(100,100), color=(255,0,0))
        file_obj2.name = 'singleredimage.png'
        image.save(file_obj2, 'png')
        file_obj2.seek(0)

        file_obj3 = StringIO()
        image = Image.new("RGBA", size=(100,100), color=(0,0,255))
        file_obj3.name = 'singleblueimage.png'
        image.save(file_obj3, 'png')
        file_obj3.seek(0)

        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        self.client.login(username="utestuser1", password="testpassword")

        imagePostData = {"image": [file_obj, file_obj2, file_obj3]}

        response = self.client.post("/images/upload/", data=imagePostData,
                                    HTTP_ACCEPT="application/json")

        file_obj.close()
        file_obj2.close()
        file_obj3.close()

        self.assertTrue(response.status_code == 200 or 201,
                         "Multiple image upload responded as not OK: %d" % response.status_code)

        responseContent = json.loads(response.content)

        self.assertTrue(responseContent, "No content returned")
        self.assertTrue(len(responseContent) == 3,
                        "Response payload says there are more than 3 images: %d" % len(responseContent))

