from django.test import TestCase
from django.core.files.base import ContentFile

from post.models import Post, AuthorPost
from images import models as img_models 
from author.models import Author, RemoteAuthor

from django.contrib.auth.models import User

from PIL import Image
from StringIO import StringIO

import uuid
import urllib
import json

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


# Create your tests here.
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

    def testRESTAddImageToPost(self):
        """
        Tests adding images to a post via a put request, then retreiving it
        with a get request.
        """
     # Authenicate and put a new post
        images = []
        user1 = User.objects.get(username="utestuser1")
        author1 = Author.objects.get(user=user1)
        self.client.login(username="utestuser1", password="testpassword")

        file_obj = StringIO()
        image = Image.new("RGBA", size=(50,50), color=(255,0,0, 0))
        file_obj.name = 'utestimage4.png'
        image.save(file_obj, 'png')
        file_obj.seek(0)

        encoded = file_obj.read().encode("base64")
        images.append([file_obj.name, "data:image/png;base64," + encoded])

        query = urllib.urlencode({"id":author1.guid})
        newPostId = str(uuid.uuid4())

        # Make a new post with minimum fields required
        newPostRequestData = { "title":"title", 
                               "content":"post1", 
                               "images":images}
        response = self.client.put('/api/post/%s?%s' % (newPostId, query),
                                    data=json.dumps(newPostRequestData),
                                    content_type="application/json")

        self.assertEqual(response.status_code, 201)

        # Want to get the new post 
        getResponse = self.client.get('/api/post/%s?%s' % (newPostId, query),
                                    HTTP_ACCEPT = 'application/json')

        self.assertEqual(getResponse.status_code, 200)
        posts = json.loads(getResponse.content, object_hook=_decode_dict)
        singlePost = posts["posts"][0]

        # Check if we can retrieve image
        response = self.client.get(singlePost["images"][0]["url"]+"/")
        self.assertEqual(response.status_code, 200)

        # Checking if image content (in base64) is equal
        self.assertEqual(response.content.encode("base64"), encoded)
        
