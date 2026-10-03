from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from accounts.models import Address, PaymentMethod, User, Voucher


class UserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email", "name", "member_since", "patron_number")


class UserUpdateForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    show_change_link = True
    fields = (
        "full_name",
        "street",
        "line2",
        "city",
        "state",
        "postal_code",
        "phone",
        "is_default",
    )


class PaymentMethodInline(admin.TabularInline):
    model = PaymentMethod
    extra = 0
    show_change_link = True
    fields = ("method", "brand", "last4", "exp_month", "exp_year", "is_default")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserUpdateForm
    add_form = UserCreationForm
    ordering = ("email",)
    list_display = (
        "email",
        "name",
        "patron_number",
        "is_staff",
        "is_active",
        "email_verified",
        "loyalty_points",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "email_verified",
        "marketing_opt_in",
    )
    search_fields = ("email", "name", "patron_number", "phone")
    readonly_fields = ("last_login", "date_joined")
    filter_horizontal = ("groups", "user_permissions")
    inlines = (AddressInline, PaymentMethodInline)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "name",
                    "phone",
                    "patron_number",
                    "member_since",
                    "loyalty_points",
                    "marketing_opt_in",
                    "email_verified",
                    "google_sub",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "member_since",
                    "patron_number",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "city", "state", "postal_code", "is_default")
    list_filter = ("is_default", "state")
    search_fields = ("full_name", "street", "city", "postal_code", "user__email", "user__name")
    ordering = ("-is_default", "city")
    autocomplete_fields = ("user",)
    list_select_related = ("user",)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "method", "brand", "last4", "is_default")
    list_filter = ("method", "is_default")
    search_fields = ("brand", "last4", "user__email", "user__name")
    ordering = ("-is_default", "method")
    autocomplete_fields = ("user",)
    list_select_related = ("user",)


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ("code", "amount", "user", "used")
    list_filter = ("used",)
    search_fields = ("code", "user__email", "user__name")
    ordering = ("code",)
    autocomplete_fields = ("user",)
    list_select_related = ("user",)
