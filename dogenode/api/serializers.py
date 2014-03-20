from rest_framework import serializers
from post.models import Post, AuthorPost
from author.models import Author

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('guid', 'title', 'description', 'content', 'visibility',
                 'contentType', 'origin', 'pubDate', 'modifiedDate')
        owner=serializers.Field(source='owner.username')


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('user', 'accepted', 'about_me')
    

class AuthorPostSerializer(serializers.ModelSerializer):
    post = serializers.PrimaryKeyRelatedField(many=False)
    author = serializers.PrimaryKeyRelatedField(many=False)

    class Meta:
        model = AuthorPost
        fields = ('author', 'post')
