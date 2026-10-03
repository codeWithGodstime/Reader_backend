import random
import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


def _next_patron_number():
    from accounts.models import User

    for _ in range(30):
        number = f"{random.randint(1000, 9999)}"
        if not User.objects.filter(patron_number=number).exists():
            return number
    return uuid.uuid4().hex[:8]


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email).lower()
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("member_since", timezone.now().date())
        extra_fields.setdefault("patron_number", _next_patron_number())
        extra_fields.setdefault("name", email.split("@")[0])
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    member_since = models.DateField()
    patron_number = models.CharField(max_length=16, unique=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    marketing_opt_in = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name="addresses", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=120)
    street = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=2)
    postal_code = models.CharField(max_length=12)
    phone = models.CharField(max_length=32)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "city"]

    def __str__(self):
        return f"{self.full_name}, {self.city}"


class PaymentMethod(models.Model):
    CARD = "card"
    PAYPAL = "paypal"
    GOOGLE_PAY = "google_pay"
    METHODS = [(CARD, "Card"), (PAYPAL, "PayPal"), (GOOGLE_PAY, "Google Pay")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name="payment_methods", on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHODS)
    brand = models.CharField(max_length=40, blank=True)
    last4 = models.CharField(max_length=4, blank=True)
    exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "method"]


class Voucher(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, related_name="vouchers", null=True, blank=True, on_delete=models.CASCADE)
    used = models.BooleanField(default=False)

    def __str__(self):
        return self.code
