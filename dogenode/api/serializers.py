from rest_framework import serializers
from post.models import Post
from author.models import Author
from comments.models import Comment
from categories.models import Category

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('user', 'host', 'displayName', 'url')

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('guid', 'author', 'post_ref', 'comment', 'pub_date')

class FullPostSerializer(serializers.Serializer):
    """
    A special way of Serializing the posts that are required in the 
    example-article.json since the model of our post doesn't quite match
    what needs to be sent
    """
    
    guid = serializers.CharField(max_length=36)
    title = serializers.CharField(max_length=140)
    description = serializers.CharField(max_length=255) 
    # CharField for content corresponds to TextField
    content = serializers.CharField(max_length=None, min_length=None)
    visibility = serializers.CharField(max_length=10)
    contentType = serializers.CharField(max_length=15)
    origin = serializers.URLField()
    pubDate = serializers.DateTimeField()
    modifiedDate = serializers.DateTimeField()

    author = AuthorSerializer()
    comments = CommentSerializer(required = False) # May have no comments    
    categories = serializers.CharField(max_length=80) 

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            # Post related fields
            instance.guid = attrs.get('guid', instance.guid)
            instance.title = attrs.get('title', instance.title)
            instance.description = attrs.get('description', 
                                             instance.description)
            instance.content = attrs.get('content', instance.content)
            instance.visibility = attrs.get('visibility', instance.visibility)
            instance.contentType = attrs.get('contentType', 
                                             instance.contentType)
            instance.origin = attrs.get('origin', instance.origin)
            instance.pubDate = attrs.get('pubDate', instance.pubDate)
            instance.modifiedDate = attrs.get('modifiedDate', 
                                              instance.modifiedDate)

            # Other models mushed in
            instance.author = attrs.get('author', instance.author)
            instance.comments = attrs.get('comments', instance.comments)
            instance.categories = attrs.get('categories', instance.categories)

            return instance
        return Post(**attrs)
    
