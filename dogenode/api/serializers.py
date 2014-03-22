from rest_framework import serializers

class AuthorSerializer(serializers.Serializer):
    """
    Custom Author Serializer that includes the fields that we need
    """
    id = serializers.CharField(max_length=36)
    host = serializers.CharField(max_length=100)
    displayName = serializers.CharField(max_length=30)
    url = serializers.URLField()

class CommentSerializer(serializers.Serializer):
    """
    Custom Comment Serializer that includes the author specially serialized
    """
    guid = serializers.CharField(max_length=36)
    comment= serializers.CharField(max_length=None,min_length=None)
    pub_date= serializers.DateTimeField()

    author = AuthorSerializer()

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
