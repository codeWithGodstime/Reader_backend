from catalog.models import Shelf
from commerce.models import Order
from common.money import money_str


def profile(user):
    voucher = user.vouchers.filter(used=False).order_by("code").first()
    active_orders = user.orders.exclude(
        status__in=[Order.DELIVERED, Order.CANCELLED]
    ).count()
    shelf_count = Shelf.objects.filter(user=user).count()
    saved_book_count = (
        Shelf.books.through.objects.filter(shelf__user=user)
        .values("book_id")
        .distinct()
        .count()
    )
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "phone": user.phone or None,
        "member_since": user.member_since.isoformat(),
        "patron_number": user.patron_number,
        "loyalty_points": user.loyalty_points,
        "voucher": (
            None
            if voucher is None
            else {
                "code": voucher.code,
                "amount": money_str(voucher.amount),
                "currency": "USD",
            }
        ),
        "marketing_opt_in": user.marketing_opt_in,
        "active_order_count": active_orders,
        "shelf_count": shelf_count,
        "saved_book_count": saved_book_count,
    }


def address_payload(address):
    return {
        "id": str(address.id),
        "full_name": address.full_name,
        "street": address.street,
        "line2": address.line2 or None,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "phone": address.phone,
        "is_default": address.is_default,
    }


def payment_payload(method):
    return {
        "id": str(method.id),
        "method": method.method,
        "brand": method.brand or None,
        "last4": method.last4 or None,
        "exp_month": method.exp_month,
        "exp_year": method.exp_year,
        "is_default": method.is_default,
    }
