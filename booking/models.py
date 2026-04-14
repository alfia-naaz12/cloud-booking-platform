from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from django.dispatch import receiver
from django.db.models.signals import post_save
from datetime import time


class Service(models.Model):
    name = models.CharField(max_length=120)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name


class Staff(models.Model):
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        return self.reviews.aggregate(
            Avg("rating")
        )["rating__avg"] or 0


class WorkingHour(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    day_of_week = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()


class Break(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    day_of_week = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

class Booking(models.Model):

    STATUS_CHOICES = [
        ("PENDING_PAYMENT", "Pending Payment"),
        ("BOOKED", "Booked"),
        ("CANCELLED", "Cancelled"),
        ("COMPLETED", "Completed"),
        ("NO_SHOW", "No Show"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING_PAYMENT"
    )

    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.service.name} ({self.status})"

class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


@receiver(post_save, sender=Staff)
def create_default_working_hours(sender, instance, created, **kwargs):
    if created:
        for day in range(7):
            WorkingHour.objects.get_or_create(
                staff=instance,
                day_of_week=day,
                defaults={"start_time": time(9, 0), "end_time": time(17, 0)},
            )