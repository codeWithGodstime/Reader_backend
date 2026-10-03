import random
import string
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from accounts.models import Address, PaymentMethod
from catalog.models import BookFormat
from commerce.models import Cart, CartItem, Order, OrderItem, TrackingEvent
from common.exceptions import APIError
from common.money import quote

FORMATS = {"paperback", "hardcover", "ebook", "signed"}
TIMELINE = [
    ("confirmed", "Confirmed"),
    ("packed", "Curated & Bound"),
    ("shipped", "Shipped"),
    ("out_for_delivery", "Out for Delivery"),
    ("delivered", "Delivered"),
]


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def edition_for(book, code):
    if code not in FORMATS:
        raise APIError(
            "Unknown edition.",
            details=[{"field": "format", "message": "Choose paperback, hardcover, ebook, or signed."}],
        )
    edition = book.formats.filter(code=code).first()
    if edition is None:
        raise APIError("That edition is not sold.", code="not_found", status_code=404)
    if not book.in_stock or not edition.in_stock:
        raise APIError(f"{book.title} is out of stock in that edition.", code="out_of_stock", status_code=409)
    return edition


def add_line(cart, book, edition, quantity):
    item = cart.items.filter(book=book, format=edition.code).first()
    new_quantity = quantity if item is None else item.quantity + quantity
    if new_quantity > 20:
        raise APIError(
            "You can add at most 20 copies of an edition.",
            details=[{"field": "quantity", "message": "Quantity cannot exceed 20."}],
        )
    if item is None:
        return CartItem.objects.create(
            cart=cart,
            book=book,
            format=edition.code,
            format_label=edition.label,
            quantity=quantity,
            unit_price=edition.price,
        )
    item.quantity = new_quantity
    item.unit_price = edition.price
    item.format_label = edition.label
    item.save(update_fields=["quantity", "unit_price", "format_label"])
    return item


def new_order_number():
    for _ in range(20):
        number = f"RD-{random.randint(10000, 99999)}"
        if not Order.objects.filter(number=number).exists():
            return number
    raise APIError("Could not allocate an order number.", code="conflict", status_code=409)


def new_tracking_number():
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    return f"RSP-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{letters}"


def build_events(status, placed_at, custom=None):
    if custom is not None:
        return custom
    codes = [code for code, _label in TIMELINE]
    current = codes.index(status) if status in codes else 0
    rows = []
    for index, (code, label) in enumerate(TIMELINE):
        if index < current:
            state = TrackingEvent.COMPLETED
            occurred = placed_at
            location = ""
        elif index == current:
            state = TrackingEvent.CURRENT
            occurred = placed_at
            location = "Reader Bookshelf Warehouse" if code == "confirmed" else ""
        else:
            state = TrackingEvent.UPCOMING
            occurred = None
            location = ""
        rows.append(
            {
                "code": code,
                "label": label,
                "location": location,
                "occurred_at": occurred,
                "state": state,
                "position": index,
            }
        )
    return rows


def create_order(
    *,
    user,
    email,
    shipping_method,
    address,
    payment,
    lines,
    subtotal,
    discount,
    shipping,
    tax,
    total,
    status=Order.CONFIRMED,
    placed_at=None,
    estimated_delivery=None,
    number=None,
    carrier="",
    tracking_number="",
    delivery_instructions="",
    events=None,
):
    placed_at = placed_at or timezone.now()
    if estimated_delivery is None and status not in {Order.DELIVERED, Order.CANCELLED}:
        days = 2 if shipping_method == Order.EXPRESS else 5
        estimated_delivery = placed_at.date() + timedelta(days=days)
    order = Order.objects.create(
        user=user,
        number=number or new_order_number(),
        status=status,
        email=email,
        placed_at=placed_at,
        estimated_delivery=estimated_delivery,
        subtotal=subtotal,
        discount=discount,
        shipping=shipping,
        tax=tax,
        total=total,
        shipping_method=shipping_method,
        delivery_instructions=delivery_instructions,
        carrier=carrier or ("Reader Shelf Post Express" if shipping_method == Order.EXPRESS else "Reader Shelf Post"),
        tracking_number=tracking_number or new_tracking_number(),
        address_full_name=address["full_name"],
        address_street=address["street"],
        address_line2=address.get("line2") or "",
        address_city=address["city"],
        address_state=address["state"],
        address_postal_code=address["postal_code"],
        address_phone=address["phone"],
        payment_method=payment["method"],
        payment_brand=payment.get("brand") or "",
        payment_last4=payment.get("last4") or "",
        payment_exp_month=payment.get("exp_month"),
        payment_exp_year=payment.get("exp_year"),
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                book=line["book"],
                title=line["title"],
                author_name=line["author_name"],
                cover_url=line["cover_url"],
                format=line["format"],
                format_label=line["format_label"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
            )
            for line in lines
        ]
    )
    TrackingEvent.objects.bulk_create(
        [
            TrackingEvent(order=order, **event)
            for event in build_events(status, placed_at, events)
        ]
    )
    return order


def remember_address(user, data):
    line2 = data.get("line2") or ""
    existing = user.addresses.filter(
        full_name=data["full_name"],
        street=data["street"],
        line2=line2,
        city=data["city"],
        state=data["state"],
        postal_code=data["postal_code"],
        phone=data["phone"],
    ).first()
    user.addresses.update(is_default=False)
    if existing:
        existing.is_default = True
        existing.save(update_fields=["is_default"])
        return existing
    return Address.objects.create(
        user=user,
        full_name=data["full_name"],
        street=data["street"],
        line2=line2,
        city=data["city"],
        state=data["state"],
        postal_code=data["postal_code"],
        phone=data["phone"],
        is_default=True,
    )


def remember_payment(user, data):
    existing = user.payment_methods.filter(
        method=data["method"],
        brand=data.get("brand") or "",
        last4=data.get("last4") or "",
        exp_month=data.get("exp_month"),
        exp_year=data.get("exp_year"),
    ).first()
    user.payment_methods.update(is_default=False)
    if existing:
        existing.is_default = True
        existing.save(update_fields=["is_default"])
        return existing
    return PaymentMethod.objects.create(
        user=user,
        method=data["method"],
        brand=data.get("brand") or "",
        last4=data.get("last4") or "",
        exp_month=data.get("exp_month"),
        exp_year=data.get("exp_year"),
        is_default=True,
    )


def _lines_from_cart(items):
    lines = []
    for item in items:
        edition = item.book.formats.filter(code=item.format).first()
        if edition is None or not item.book.in_stock or not edition.in_stock:
            raise APIError(f"{item.book.title} is out of stock.", code="out_of_stock", status_code=409)
        lines.append(
            {
                "book": item.book,
                "title": item.book.title,
                "author_name": item.book.author.name,
                "cover_url": item.book.cover_url,
                "format": item.format,
                "format_label": item.format_label,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
        )
    return lines


def checkout_cart(user, payload):
    with transaction.atomic():
        cart, _ = Cart.objects.get_or_create(user=user)
        cart = Cart.objects.select_for_update().select_related("voucher").get(pk=cart.pk)
        items = list(cart.items.select_related("book__author"))
        if not items:
            raise APIError("Your cart is empty.", code="empty_cart", status_code=409)
        lines = _lines_from_cart(items)
        subtotal = sum((item.unit_price * item.quantity for item in items), Decimal("0"))
        voucher = cart.voucher
        if voucher is not None and (voucher.used or (voucher.user_id and voucher.user_id != user.id)):
            raise APIError("That voucher can no longer be applied.", code="conflict", status_code=409)
        discount = voucher.amount if voucher is not None else Decimal("0")
        priced = quote(subtotal, discount, payload["shipping_method"])
        order = create_order(
            user=user,
            email=payload["email"],
            shipping_method=payload["shipping_method"],
            address=payload["address"],
            payment=payload["payment"],
            lines=lines,
            subtotal=priced.subtotal,
            discount=priced.discount,
            shipping=priced.shipping,
            tax=priced.tax,
            total=priced.total,
        )
        if voucher is not None:
            voucher.used = True
            voucher.save(update_fields=["used"])
        cart.items.all().delete()
        cart.voucher = None
        cart.save(update_fields=["voucher"])
        if payload["address"].get("save"):
            remember_address(user, payload["address"])
        if payload["payment"].get("save"):
            remember_payment(user, payload["payment"])
        user.marketing_opt_in = bool(payload.get("marketing_opt_in", False))
        user.loyalty_points += int(priced.merchandise)
        user.save(update_fields=["marketing_opt_in", "loyalty_points"])
        return order


def one_click_buy(user, book, edition, quantity):
    address = user.addresses.filter(is_default=True).first()
    payment = user.payment_methods.filter(is_default=True).first()
    if address is None or payment is None:
        raise APIError(
            "Add a default address and payment method before 1-click buy.",
            code="checkout_not_ready",
            status_code=409,
        )
    unit = edition.price
    subtotal = unit * quantity
    priced = quote(subtotal, Decimal("0"), Order.STANDARD)
    with transaction.atomic():
        order = create_order(
            user=user,
            email=user.email,
            shipping_method=Order.STANDARD,
            address={
                "full_name": address.full_name,
                "street": address.street,
                "line2": address.line2,
                "city": address.city,
                "state": address.state,
                "postal_code": address.postal_code,
                "phone": address.phone,
            },
            payment={
                "method": payment.method,
                "brand": payment.brand,
                "last4": payment.last4,
                "exp_month": payment.exp_month,
                "exp_year": payment.exp_year,
            },
            lines=[
                {
                    "book": book,
                    "title": book.title,
                    "author_name": book.author.name,
                    "cover_url": book.cover_url,
                    "format": edition.code,
                    "format_label": edition.label,
                    "quantity": quantity,
                    "unit_price": unit,
                }
            ],
            subtotal=priced.subtotal,
            discount=priced.discount,
            shipping=priced.shipping,
            tax=priced.tax,
            total=priced.total,
        )
        user.loyalty_points += int(priced.merchandise)
        user.save(update_fields=["loyalty_points"])
        return order


def buy_again(user, order):
    planned = []
    for item in order.items.select_related("book__author"):
        if item.book_id is None:
            raise APIError("An edition on this order is no longer sold.", code="conflict", status_code=409)
        edition = item.book.formats.filter(code=item.format).first()
        if edition is None:
            raise APIError("An edition on this order is no longer sold.", code="conflict", status_code=409)
        if not item.book.in_stock or not edition.in_stock:
            raise APIError("An edition on this order is out of stock.", code="out_of_stock", status_code=409)
        planned.append((item.book, edition, item.quantity))
    with transaction.atomic():
        cart = get_cart(user)
        for book, edition, quantity in planned:
            add_line(cart, book, edition, quantity)
        return cart
