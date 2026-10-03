from django.contrib import admin

from commerce.models import (
    Cart,
    CartItem,
    Faq,
    NewsletterSubscription,
    Order,
    OrderItem,
    SupportMessage,
    TrackingEvent,
)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    show_change_link = True
    autocomplete_fields = ("book",)
    fields = ("book", "format", "format_label", "quantity", "unit_price")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    show_change_link = True
    ordering = ("title",)
    autocomplete_fields = ("book",)
    fields = ("title", "author_name", "format", "quantity", "unit_price", "book")


class TrackingEventInline(admin.TabularInline):
    model = TrackingEvent
    extra = 0
    show_change_link = True
    ordering = ("position",)
    fields = ("position", "code", "label", "location", "occurred_at", "state")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "voucher")
    search_fields = ("user__email", "user__name", "voucher__code")
    autocomplete_fields = ("user", "voucher")
    list_select_related = ("user", "voucher")
    inlines = (CartItemInline,)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "book", "format", "quantity", "unit_price")
    list_filter = ("format",)
    search_fields = ("book__title", "book__sku", "cart__user__email", "format_label")
    autocomplete_fields = ("book",)
    list_select_related = ("cart", "cart__user", "book")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "email", "total", "placed_at")
    list_filter = ("status", "shipping_method")
    search_fields = ("number", "email", "tracking_number", "user__email", "user__name")
    ordering = ("-placed_at",)
    autocomplete_fields = ("user",)
    list_select_related = ("user",)
    date_hierarchy = "placed_at"
    inlines = (OrderItemInline, TrackingEventInline)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "format", "quantity", "unit_price")
    list_filter = ("format",)
    search_fields = ("title", "author_name", "order__number")
    ordering = ("title",)
    autocomplete_fields = ("book",)
    list_select_related = ("order", "book")


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display = ("order", "code", "label", "state", "occurred_at", "position")
    list_filter = ("state", "code")
    search_fields = ("label", "location", "code", "order__number")
    ordering = ("position",)
    list_select_related = ("order",)


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    search_fields = ("email",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("email", "subject", "order_number", "created_at")
    search_fields = ("email", "subject", "order_number", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = ("topic", "question", "position")
    list_filter = ("topic",)
    search_fields = ("question", "answer", "topic")
    ordering = ("position",)
