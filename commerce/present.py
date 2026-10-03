from common.money import money_str
from catalog.present import isoformat_z


def line_money(unit_price, quantity):
    from common.money import q

    return q(unit_price) * quantity


def cart_item_payload(item):
    total = line_money(item.unit_price, item.quantity)
    return {
        "id": str(item.id),
        "book_id": str(item.book_id),
        "title": item.book.title,
        "author_name": item.book.author.name,
        "cover_url": item.book.cover_url,
        "format": item.format,
        "format_label": item.format_label,
        "quantity": item.quantity,
        "unit_price": money_str(item.unit_price),
        "line_total": money_str(total),
        "currency": "USD",
    }


def cart_payload(cart):
    from decimal import Decimal

    from common.money import FREE_SHIPPING_THRESHOLD, quote

    items = list(cart.items.select_related("book__author"))
    subtotal = sum((line_money(item.unit_price, item.quantity) for item in items), Decimal("0"))
    voucher = cart.voucher if cart.voucher_id and not cart.voucher.used else None
    discount = voucher.amount if voucher is not None else Decimal("0")
    priced = quote(subtotal, discount, "standard")
    return {
        "id": str(cart.id),
        "items": [cart_item_payload(item) for item in items],
        "item_count": sum(item.quantity for item in items),
        "currency": "USD",
        "subtotal": money_str(priced.subtotal),
        "discount": money_str(priced.discount),
        "shipping": money_str(priced.shipping),
        "tax": money_str(priced.tax),
        "total": money_str(priced.total),
        "voucher": (
            None
            if voucher is None
            else {"code": voucher.code, "amount": money_str(voucher.amount), "currency": "USD"}
        ),
        "free_shipping_threshold": money_str(FREE_SHIPPING_THRESHOLD),
        "amount_until_free_shipping": money_str(priced.amount_until_free_shipping),
    }


def order_item_payload(item):
    total = line_money(item.unit_price, item.quantity)
    return {
        "book_id": str(item.book_id) if item.book_id else None,
        "title": item.title,
        "author_name": item.author_name,
        "cover_url": item.cover_url,
        "format": item.format,
        "format_label": item.format_label,
        "quantity": item.quantity,
        "unit_price": money_str(item.unit_price),
        "line_total": money_str(total),
        "currency": "USD",
    }


def address_snapshot(order):
    return {
        "full_name": order.address_full_name,
        "street": order.address_street,
        "line2": order.address_line2 or None,
        "city": order.address_city,
        "state": order.address_state,
        "postal_code": order.address_postal_code,
        "phone": order.address_phone,
    }


def payment_snapshot(order):
    return {
        "method": order.payment_method,
        "brand": order.payment_brand or None,
        "last4": order.payment_last4 or None,
        "exp_month": order.payment_exp_month,
        "exp_year": order.payment_exp_year,
    }


def order_payload(order):
    items = list(order.items.all())
    return {
        "id": str(order.id),
        "number": order.number,
        "status": order.status,
        "email": order.email,
        "placed_at": isoformat_z(order.placed_at),
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        "currency": "USD",
        "subtotal": money_str(order.subtotal),
        "discount": money_str(order.discount),
        "shipping": money_str(order.shipping),
        "tax": money_str(order.tax),
        "total": money_str(order.total),
        "shipping_method": order.shipping_method,
        "item_count": sum(item.quantity for item in items),
        "items": [order_item_payload(item) for item in items],
        "address": address_snapshot(order),
        "payment": payment_snapshot(order),
        "tracking_number": order.tracking_number or None,
        "carrier": order.carrier or None,
        "delivery_instructions": order.delivery_instructions,
    }


def tracking_payload(order):
    return {
        "order_id": str(order.id),
        "number": order.number,
        "status": order.status,
        "carrier": order.carrier or None,
        "tracking_number": order.tracking_number or None,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        "events": [
            {
                "code": event.code,
                "label": event.label,
                "location": event.location or None,
                "occurred_at": isoformat_z(event.occurred_at),
                "state": event.state,
            }
            for event in order.events.all()
        ],
    }


def invoice_payload(order):
    items = list(order.items.all())
    return {
        "order_id": str(order.id),
        "number": order.number,
        "placed_at": isoformat_z(order.placed_at),
        "email": order.email,
        "ship_to": address_snapshot(order),
        "items": [order_item_payload(item) for item in items],
        "subtotal": money_str(order.subtotal),
        "discount": money_str(order.discount),
        "shipping": money_str(order.shipping),
        "tax": money_str(order.tax),
        "total": money_str(order.total),
        "currency": "USD",
        "payment": payment_snapshot(order),
    }
