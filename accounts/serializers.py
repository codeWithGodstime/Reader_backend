from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from common.exceptions import APIError
from common.states import US_STATES


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise APIError(
                "Invalid password.",
                details=[{"field": "password", "message": " ".join(exc.messages)}],
            ) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class ProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    phone = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)
    marketing_opt_in = serializers.BooleanField(required=False)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_phone(self, value):
        if value is None:
            return ""
        return value.strip()


class AddressWriteSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120)
    street = serializers.CharField(max_length=200)
    line2 = serializers.CharField(
        max_length=200, required=False, allow_null=True, allow_blank=True, default=""
    )
    city = serializers.CharField(max_length=80)
    state = serializers.CharField(min_length=2, max_length=2)
    postal_code = serializers.CharField(max_length=12)
    phone = serializers.CharField(max_length=32)
    is_default = serializers.BooleanField(required=False, default=False)

    def validate_state(self, value):
        value = value.strip().upper()
        if value not in US_STATES:
            raise serializers.ValidationError("Enter a two-letter US state code.")
        return value

    def validate_line2(self, value):
        if not value:
            return ""
        return value.strip()

    def validate(self, attrs):
        for field in ("full_name", "street", "city", "postal_code", "phone"):
            attrs[field] = attrs[field].strip()
            if not attrs[field]:
                raise serializers.ValidationError({field: "This field is required."})
        return attrs


class PaymentWriteSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["card", "paypal", "google_pay"])
    brand = serializers.CharField(max_length=40, required=False, allow_null=True, allow_blank=True)
    last4 = serializers.CharField(max_length=4, required=False, allow_null=True, allow_blank=True)
    exp_month = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=12)
    exp_year = serializers.IntegerField(required=False, allow_null=True, min_value=2024, max_value=2100)
    is_default = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs["method"] != "card":
            attrs["brand"] = ""
            attrs["last4"] = ""
            attrs["exp_month"] = None
            attrs["exp_year"] = None
            return attrs
        details = []
        brand = (attrs.get("brand") or "").strip()
        last4 = (attrs.get("last4") or "").strip()
        if not brand:
            details.append({"field": "brand", "message": "Card brand is required."})
        if len(last4) != 4 or not last4.isdigit():
            details.append({"field": "last4", "message": "Enter the last four digits."})
        if attrs.get("exp_month") is None:
            details.append({"field": "exp_month", "message": "Expiration month is required."})
        if attrs.get("exp_year") is None:
            details.append({"field": "exp_year", "message": "Expiration year is required."})
        if details:
            raise APIError("Invalid payment details.", details=details)
        attrs["brand"] = brand
        attrs["last4"] = last4
        return attrs
