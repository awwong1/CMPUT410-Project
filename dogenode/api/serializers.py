from rest_framework import serializers

class AuthorSerializer(serializers.Serializer):
    """
    Custom Author Serializer that includes the fields that we need
    """
    id = serializers.CharField(max_length=36)
    host = serializers.CharField(max_length=100)
    displayname = serializers.CharField(max_length=30)
    url = serializers.URLField()

class CommentSerializer(serializers.Serializer):
    """
    Custom Comment Serializer that includes the author specially serialized
    """
    guid = serializers.CharField(max_length=36)
    comment= serializers.CharField(max_length=None,min_length=None)
    pub_date= serializers.DateTimeField(format="%a %b %d %H:%M:%S %Z %Y")

    author = AuthorSerializer()


class ImageSerializer(serializers.Serializer):
    """
    Custom Images Serializer
    """
    id = serializers.IntegerField()
    visibility = serializers.CharField()
    url = serializers.URLField()

class FullPostSerializer(serializers.Serializer):
    """
    A special way of Serializing the posts that are required in the 
    example-article.json since the model of our post doesn't quite match
    what needs to be sent
    """
    guid = serializers.CharField(max_length=36, required=False)
    title = serializers.CharField(max_length=140, required=False)
    description = serializers.CharField(max_length=255, required=False) 
    # CharField for content corresponds to TextField
    content = serializers.CharField(max_length=None, min_length=None, required=False)
    visibility = serializers.CharField(max_length=10, required=False)
    contentType = serializers.CharField(max_length=15, required=False)
    origin = serializers.URLField(required=False)
    pubDate = serializers.DateTimeField(required=False, 
                                        format="%a %b %d %H:%M:%S %Z %Y")
    modifiedDate = serializers.DateTimeField(required=False,
                                        format="%a %b %d %H:%M:%S %Z %Y")

    author = AuthorSerializer(required=False)
    comments = CommentSerializer(required = False) # May have no comments    
    categories = serializers.CharField(max_length=80, required=False)
    # Other Authors who can view the post outside of normal visibility options
    visibilityExceptions = AuthorSerializer(required=False) 
    images = ImageSerializer(required=False)

