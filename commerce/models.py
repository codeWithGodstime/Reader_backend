import uuid

from django.conf import settings
from django.db import models

from catalog.models import Book


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="cart", on_delete=models.CASCADE)
    voucher = models.ForeignKey(
        "accounts.Voucher",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="carts",
    )


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    format = models.CharField(max_length=20)
    format_label = models.CharField(max_length=40)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "book", "format"], name="unique_cart_line"),
        ]


class Order(models.Model):
    CONFIRMED = "confirmed"
    PACKED = "packed"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    STATUSES = [
        (CONFIRMED, "Confirmed"),
        (PACKED, "Packed"),
        (SHIPPED, "Shipped"),
        (OUT_FOR_DELIVERY, "Out for delivery"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
    ]
    STANDARD = "standard"
    EXPRESS = "express"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE)
    number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUSES)
    email = models.EmailField()
    placed_at = models.DateTimeField()
    estimated_delivery = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_method = models.CharField(max_length=20)
    delivery_instructions = models.TextField(blank=True)
    carrier = models.CharField(max_length=80, blank=True)
    tracking_number = models.CharField(max_length=40, blank=True)
    address_full_name = models.CharField(max_length=120)
    address_street = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    address_city = models.CharField(max_length=80)
    address_state = models.CharField(max_length=2)
    address_postal_code = models.CharField(max_length=12)
    address_phone = models.CharField(max_length=32)
    payment_method = models.CharField(max_length=20)
    payment_brand = models.CharField(max_length=40, blank=True)
    payment_last4 = models.CharField(max_length=4, blank=True)
    payment_exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    payment_exp_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-placed_at"]


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=200)
    author_name = models.CharField(max_length=160)
    cover_url = models.URLField(max_length=500)
    format = models.CharField(max_length=20)
    format_label = models.CharField(max_length=40)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["title"]


class TrackingEvent(models.Model):
    COMPLETED = "completed"
    CURRENT = "current"
    UPCOMING = "upcoming"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name="events", on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    label = models.CharField(max_length=80)
    location = models.CharField(max_length=160, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]


class NewsletterSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SupportMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    subject = models.CharField(max_length=160)
    message = models.TextField()
    order_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Faq(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=20)
    question = models.CharField(max_length=200)
    answer = models.TextField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
