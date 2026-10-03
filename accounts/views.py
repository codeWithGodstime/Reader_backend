from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.google import verify_google_id_token
from accounts.models import Address, PaymentMethod, User
from accounts.present import address_payload, payment_payload, profile
from accounts.serializers import (
    AddressWriteSerializer,
    LoginSerializer,
    PaymentWriteSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
)
from common.exceptions import APIError


def auth_response(user, status):
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": profile(user),
        },
        status=status,
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise APIError(
                "An account with this email already exists.",
                code="conflict",
                status_code=409,
            )
        try:
            user = User.objects.create_user(
                email=email,
                password=serializer.validated_data["password"],
                name=serializer.validated_data["name"],
            )
        except IntegrityError as exc:
            raise APIError(
                "An account with this email already exists.",
                code="conflict",
                status_code=409,
            ) from exc
        return auth_response(user, 201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise APIError(
                "Email or password is incorrect.",
                code="authentication_failed",
                status_code=401,
            )
        return auth_response(user, 200)


class GoogleSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.data.get("id_token") if isinstance(request.data, dict) else None
        if not isinstance(raw, str) or not raw.strip():
            raise APIError(
                "Google ID token is required.",
                code="authentication_failed",
                status_code=401,
            )
        claims = verify_google_id_token(raw.strip())
        taken = User.objects.filter(google_sub=claims["sub"]).exclude(email=claims["email"]).exists()
        if taken:
            raise APIError(
                "This Google account is already linked to another reader.",
                code="conflict",
                status_code=409,
            )
        user = User.objects.filter(email=claims["email"]).first()
        if user is None:
            try:
                user = User.objects.create_user(
                    email=claims["email"],
                    password=None,
                    name=claims["name"],
                    google_sub=claims["sub"],
                    email_verified=True,
                )
            except IntegrityError as exc:
                raise APIError(
                    "An account with this email already exists.",
                    code="conflict",
                    status_code=409,
                ) from exc
        else:
            user.google_sub = claims["sub"]
            user.email_verified = True
            user.save(update_fields=["google_sub", "email_verified"])
        return auth_response(user, 200)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise APIError(
                "Refresh token is invalid.",
                code="authentication_failed",
                status_code=401,
            ) from exc
        data = serializer.validated_data
        return Response({"access": data["access"], "refresh": data["refresh"]})


class LogoutView(APIView):
    def post(self, request):
        raw = request.data.get("refresh") if isinstance(request.data, dict) else None
        if not isinstance(raw, str) or not raw:
            raise APIError(
                "Refresh token is required.",
                details=[{"field": "refresh", "message": "This field is required."}],
            )
        try:
            token = RefreshToken(raw)
        except TokenError as exc:
            raise APIError(
                "Refresh token is invalid.",
                code="authentication_failed",
                status_code=401,
            ) from exc
        if str(token.get("user_id")) != str(request.user.id):
            raise APIError(
                "Refresh token is invalid.",
                code="authentication_failed",
                status_code=401,
            )
        token.blacklist()
        return Response(status=204)


class MeView(APIView):
    def get(self, request):
        return Response(profile(request.user))

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if "name" in serializer.validated_data:
            user.name = serializer.validated_data["name"]
        if "phone" in serializer.validated_data:
            user.phone = serializer.validated_data["phone"]
        if "marketing_opt_in" in serializer.validated_data:
            user.marketing_opt_in = serializer.validated_data["marketing_opt_in"]
        user.save()
        return Response(profile(user))


class AddressListView(APIView):
    def get(self, request):
        rows = request.user.addresses.all()
        return Response([address_payload(row) for row in rows])

    def post(self, request):
        serializer = AddressWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        make_default = data["is_default"] or not request.user.addresses.exists()
        with transaction.atomic():
            if make_default:
                request.user.addresses.update(is_default=False)
            address = Address.objects.create(
                user=request.user,
                full_name=data["full_name"],
                street=data["street"],
                line2=data["line2"],
                city=data["city"],
                state=data["state"],
                postal_code=data["postal_code"],
                phone=data["phone"],
                is_default=make_default,
            )
        return Response(address_payload(address), status=201)


class AddressDetailView(APIView):
    def _get(self, request, address_id):
        address = request.user.addresses.filter(pk=address_id).first()
        if address is None:
            raise APIError("Address not found.", code="not_found", status_code=404)
        return address

    def patch(self, request, address_id):
        address = self._get(request, address_id)
        serializer = AddressWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            if data["is_default"]:
                request.user.addresses.exclude(pk=address.pk).update(is_default=False)
            for field in ("full_name", "street", "line2", "city", "state", "postal_code", "phone", "is_default"):
                setattr(address, field, data[field])
            address.save()
        return Response(address_payload(address))

    def delete(self, request, address_id):
        address = self._get(request, address_id)
        was_default = address.is_default
        address.delete()
        if was_default:
            nxt = request.user.addresses.first()
            if nxt is not None:
                nxt.is_default = True
                nxt.save(update_fields=["is_default"])
        return Response(status=204)


class PaymentListView(APIView):
    def get(self, request):
        return Response([payment_payload(row) for row in request.user.payment_methods.all()])

    def post(self, request):
        serializer = PaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        make_default = data["is_default"] or not request.user.payment_methods.exists()
        with transaction.atomic():
            if make_default:
                request.user.payment_methods.update(is_default=False)
            method = PaymentMethod.objects.create(
                user=request.user,
                method=data["method"],
                brand=data["brand"],
                last4=data["last4"],
                exp_month=data["exp_month"],
                exp_year=data["exp_year"],
                is_default=make_default,
            )
        return Response(payment_payload(method), status=201)


class PaymentDetailView(APIView):
    def delete(self, request, payment_method_id):
        method = request.user.payment_methods.filter(pk=payment_method_id).first()
        if method is None:
            raise APIError("Payment method not found.", code="not_found", status_code=404)
        was_default = method.is_default
        method.delete()
        if was_default:
            nxt = request.user.payment_methods.first()
            if nxt is not None:
                nxt.is_default = True
                nxt.save(update_fields=["is_default"])
        return Response(status=204)
