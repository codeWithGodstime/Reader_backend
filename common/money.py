from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

FREE_SHIPPING_THRESHOLD = Decimal("35.00")
STANDARD_SHIPPING = Decimal("5.99")
EXPRESS_SHIPPING = Decimal("4.99")
TAX_RATE = Decimal("0.08")


def q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_str(value) -> str:
    return f"{q(value):.2f}"


@dataclass
class Quote:
    subtotal: Decimal
    discount: Decimal
    merchandise: Decimal
    shipping: Decimal
    tax: Decimal
    total: Decimal
    amount_until_free_shipping: Decimal


def quote(subtotal, discount, method: str) -> Quote:
    subtotal = q(subtotal)
    discount = q(min(q(discount), subtotal))
    merchandise = q(subtotal - discount)
    if method == "express":
        shipping = EXPRESS_SHIPPING
    elif merchandise >= FREE_SHIPPING_THRESHOLD:
        shipping = Decimal("0.00")
    else:
        shipping = STANDARD_SHIPPING
    tax = q(merchandise * TAX_RATE)
    total = q(merchandise + shipping + tax)
    if merchandise >= FREE_SHIPPING_THRESHOLD:
        until = Decimal("0.00")
    else:
        until = q(FREE_SHIPPING_THRESHOLD - merchandise)
    return Quote(subtotal, discount, merchandise, shipping, tax, total, until)
