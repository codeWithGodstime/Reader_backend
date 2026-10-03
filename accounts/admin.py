from django.contrib import admin

from accounts.models import Address, PaymentMethod, User, Voucher

admin.site.register(User)
admin.site.register(Address)
admin.site.register(PaymentMethod)
admin.site.register(Voucher)
