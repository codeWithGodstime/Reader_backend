from decimal import Decimal, InvalidOperation

from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Voucher
from catalog.models import Book
from catalog.present import isoformat_z
from commerce.models import Faq, NewsletterSubscription, Order, SupportMessage
from commerce.present import cart_payload, invoice_payload, order_payload, tracking_payload
from commerce.serializers import (
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
    CheckoutSerializer,
    DeliverySerializer,
    NewsletterSerializer,
    OneClickSerializer,
    SupportSerializer,
    VoucherSerializer,
)
from commerce.services import (
    add_line,
    buy_again,
    checkout_cart,
    edition_for,
    get_cart,
    one_click_buy,
)
from common.exceptions import APIError
from common.money import quote
from common.pagination import ReaderPagination


def _book_or_404(book_id):
    book = Book.objects.select_related("author").filter(pk=book_id).first()
    if book is None:
        raise APIError("Book not found.", code="not_found", status_code=404)
    return book


def _order_or_404(user, order_id):
    order = (
        Order.objects.filter(user=user, pk=order_id)
        .prefetch_related("items", "events")
        .first()
    )
    if order is None:
        raise APIError("Order not found.", code="not_found", status_code=404)
    return order


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class CartView(APIView):
    def get(self, request):
        return Response(cart_payload(get_cart(request.user)))


class CartItemListView(APIView):
    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        book = _book_or_404(data["book_id"])
        edition = edition_for(book, data["format"])
        cart = get_cart(request.user)
        add_line(cart, book, edition, data["quantity"])
        return Response(cart_payload(cart))


class CartItemDetailView(APIView):
    def _item(self, request, item_id):
        cart = get_cart(request.user)
        item = cart.items.select_related("book").filter(pk=item_id).first()
        if item is None:
            raise APIError("Cart item not found.", code="not_found", status_code=404)
        return cart, item

    def patch(self, request, item_id):
        cart, item = self._item(request, item_id)
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]
        if quantity == 0:
            item.delete()
        else:
            edition = item.book.formats.filter(code=item.format).first()
            item.quantity = quantity
            if edition is not None:
                item.unit_price = edition.price
                item.format_label = edition.label
            item.save()
        return Response(cart_payload(cart))

    def delete(self, request, item_id):
        cart, item = self._item(request, item_id)
        item.delete()
        return Response(cart_payload(cart))


class CartVoucherView(APIView):
    def post(self, request):
        serializer = VoucherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        voucher = Voucher.objects.filter(code=code, used=False).first()
        if voucher is None or (voucher.user_id and voucher.user_id != request.user.id):
            raise APIError("Voucher not found.", code="not_found", status_code=404)
        cart = get_cart(request.user)
        cart.voucher = voucher
        cart.save(update_fields=["voucher"])
        return Response(cart_payload(cart))

    def delete(self, request):
        cart = get_cart(request.user)
        cart.voucher = None
        cart.save(update_fields=["voucher"])
        return Response(cart_payload(cart))


class ShippingMethodView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raw = request.query_params.get("subtotal", "0.00") or "0.00"
        try:
            subtotal = Decimal(raw)
        except InvalidOperation as exc:
            raise APIError(
                "Invalid subtotal.",
                details=[{"field": "subtotal", "message": "Enter a decimal amount."}],
            ) from exc
        if subtotal < 0:
            raise APIError(
                "Invalid subtotal.",
                details=[{"field": "subtotal", "message": "Subtotal cannot be negative."}],
            )
        catalog = {
            "standard": ("Standard Ground", "Hand-wrapped in recyclable paper", "3–5 business days"),
            "express": ("Priority Express", "Expedited priority handling and tracking", "1–2 business days"),
        }
        rows = []
        for code, (label, detail, eta) in catalog.items():
            priced = quote(subtotal, Decimal("0"), code)
            rows.append(
                {
                    "code": code,
                    "label": label,
                    "detail": detail,
                    "price": f"{priced.shipping:.2f}",
                    "currency": "USD",
                    "eta": eta,
                }
            )
        return Response(rows)


class CheckoutView(APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = checkout_cart(request.user, serializer.validated_data)
        order = _order_or_404(request.user, order.id)
        return Response(order_payload(order), status=201)


class OneClickView(APIView):
    def post(self, request):
        serializer = OneClickSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        book = _book_or_404(data["book_id"])
        edition = edition_for(book, data["format"])
        order = one_click_buy(request.user, book, edition, data["quantity"])
        order = _order_or_404(request.user, order.id)
        return Response(order_payload(order), status=201)


class OrderListView(APIView):
    def get(self, request):
        status = request.query_params.get("status", "all") or "all"
        if status not in {"all", "active", "past"}:
            raise APIError(
                "Unknown status filter.",
                details=[{"field": "status", "message": "Use all, active, or past."}],
            )
        qs = Order.objects.filter(user=request.user).prefetch_related("items")
        if status == "active":
            qs = qs.exclude(status__in=[Order.DELIVERED, Order.CANCELLED])
        elif status == "past":
            qs = qs.filter(status__in=[Order.DELIVERED, Order.CANCELLED])
        query = (request.query_params.get("q") or "").strip()
        if query:
            qs = qs.filter(Q(number__icontains=query) | Q(items__title__icontains=query)).distinct()
        paginator = ReaderPagination()
        page = paginator.paginate_queryset(qs.order_by("-placed_at"), request, view=self)
        return paginator.get_paginated_response([order_payload(order) for order in page])


class OrderDetailView(APIView):
    def get(self, request, order_id):
        return Response(order_payload(_order_or_404(request.user, order_id)))

    def patch(self, request, order_id):
        order = _order_or_404(request.user, order_id)
        if order.status in {Order.DELIVERED, Order.CANCELLED}:
            raise APIError(
                "This order can no longer change delivery instructions.",
                code="conflict",
                status_code=409,
            )
        serializer = DeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.delivery_instructions = serializer.validated_data["delivery_instructions"]
        order.save(update_fields=["delivery_instructions"])
        return Response(order_payload(order))


class TrackingView(APIView):
    def get(self, request, order_id):
        return Response(tracking_payload(_order_or_404(request.user, order_id)))


class InvoiceView(APIView):
    def get(self, request, order_id):
        return Response(invoice_payload(_order_or_404(request.user, order_id)))


class BuyAgainView(APIView):
    def post(self, request, order_id):
        order = _order_or_404(request.user, order_id)
        cart = buy_again(request.user, order)
        return Response(cart_payload(cart))


class NewsletterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = NewsletterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        _subscription, created = NewsletterSubscription.objects.get_or_create(email=email)
        return Response({"email": email, "subscribed": True}, status=201 if created else 200)


class FaqListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            [
                {
                    "id": str(faq.id),
                    "topic": faq.topic,
                    "question": faq.question,
                    "answer": faq.answer,
                }
                for faq in Faq.objects.all()
            ]
        )


class SupportMessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SupportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        message = SupportMessage.objects.create(
            email=data["email"].lower(),
            subject=data["subject"],
            message=data["message"],
            order_number=data.get("order_number") or "",
        )
        return Response(
            {
                "id": str(message.id),
                "email": message.email,
                "subject": message.subject,
                "message": message.message,
                "order_number": message.order_number or None,
                "created_at": isoformat_z(message.created_at),
            },
            status=201,
        )
