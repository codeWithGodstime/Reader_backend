from django.urls import path

from commerce.views import (
    BuyAgainView,
    CartItemDetailView,
    CartItemListView,
    CartVoucherView,
    CartView,
    CheckoutView,
    FaqListView,
    HealthView,
    InvoiceView,
    NewsletterView,
    OneClickView,
    OrderDetailView,
    OrderListView,
    ShippingMethodView,
    SupportMessageView,
    TrackingView,
)

urlpatterns = [
    path("health", HealthView.as_view()),
    path("cart", CartView.as_view()),
    path("cart/items", CartItemListView.as_view()),
    path("cart/items/<uuid:item_id>", CartItemDetailView.as_view()),
    path("cart/voucher", CartVoucherView.as_view()),
    path("shipping-methods", ShippingMethodView.as_view()),
    path("checkout", CheckoutView.as_view()),
    path("checkout/one-click", OneClickView.as_view()),
    path("orders", OrderListView.as_view()),
    path("orders/<uuid:order_id>", OrderDetailView.as_view()),
    path("orders/<uuid:order_id>/tracking", TrackingView.as_view()),
    path("orders/<uuid:order_id>/invoice", InvoiceView.as_view()),
    path("orders/<uuid:order_id>/buy-again", BuyAgainView.as_view()),
    path("newsletter/subscriptions", NewsletterView.as_view()),
    path("support/faqs", FaqListView.as_view()),
    path("support/messages", SupportMessageView.as_view()),
]
