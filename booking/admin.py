from django.contrib import admin

# Register your models here.
from .models import Service, Staff, WorkingHour, Break, Booking

admin.site.register(Service)
admin.site.register(Staff)
admin.site.register(WorkingHour)
admin.site.register(Break)
admin.site.register(Booking)