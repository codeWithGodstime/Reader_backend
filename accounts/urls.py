from django.urls import path

from accounts.views import (
    AddressDetailView,
    AddressListView,
    GoogleSignInView,
    LoginView,
    LogoutView,
    MeView,
    PaymentDetailView,
    PaymentListView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("auth/register", RegisterView.as_view()),
    path("auth/login", LoginView.as_view()),
    path("auth/google", GoogleSignInView.as_view()),
    path("auth/refresh", RefreshView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("me", MeView.as_view()),
    path("addresses", AddressListView.as_view()),
    path("addresses/<uuid:address_id>", AddressDetailView.as_view()),
    path("payment-methods", PaymentListView.as_view()),
    path("payment-methods/<uuid:payment_method_id>", PaymentDetailView.as_view()),
]
