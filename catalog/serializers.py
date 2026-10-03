from rest_framework import serializers


class ReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    body = serializers.CharField(max_length=4000)
    edition = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Review text is required.")
        return value


class ShelfWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value


class ShelfBookSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
