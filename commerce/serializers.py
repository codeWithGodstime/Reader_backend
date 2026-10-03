from rest_framework import serializers

from accounts.serializers import AddressWriteSerializer, PaymentWriteSerializer


class CheckoutAddressSerializer(AddressWriteSerializer):
    save = serializers.BooleanField(required=False, default=False)


class CheckoutPaymentSerializer(PaymentWriteSerializer):
    save = serializers.BooleanField(required=False, default=False)


class CheckoutSerializer(serializers.Serializer):
    email = serializers.EmailField()
    marketing_opt_in = serializers.BooleanField(required=False, default=False)
    shipping_method = serializers.ChoiceField(choices=["standard", "express"])
    address = CheckoutAddressSerializer()
    payment = CheckoutPaymentSerializer()


class OneClickSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    format = serializers.ChoiceField(choices=["paperback", "hardcover", "ebook", "signed"])
    quantity = serializers.IntegerField(required=False, min_value=1, max_value=20, default=1)


class CartItemCreateSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    format = serializers.ChoiceField(choices=["paperback", "hardcover", "ebook", "signed"])
    quantity = serializers.IntegerField(required=False, min_value=1, max_value=20, default=1)


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0, max_value=20)


class VoucherSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)

    def validate_code(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Enter a voucher code.")
        return value


class DeliverySerializer(serializers.Serializer):
    delivery_instructions = serializers.CharField(max_length=500, allow_blank=True)


class NewsletterSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SupportSerializer(serializers.Serializer):
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=160)
    message = serializers.CharField(max_length=4000)
    order_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_subject(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Subject is required.")
        return value

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Message is required.")
        return value
