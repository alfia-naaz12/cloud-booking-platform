from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Review
from .forms import ReviewForm
from .forms import CustomUserCreationForm
from .models import Staff, Service, Booking, Break, WorkingHour
from booking_scheduling_engine.engine import SchedulingEngine
from django.db.models import Count, Sum
from django.contrib.admin.views.decorators import staff_member_required


# ----------------------------
# Landing Page
# ----------------------------
def home(request):
    services = Service.objects.all()
    reviews = Review.objects.select_related("staff").order_by("-id")[:3]

    return render(request, "booking/landing.html", {
        "services": services,
        "reviews": reviews
    })


# ----------------------------
# Signup
# ----------------------------
def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect("login")
    else:
        form = CustomUserCreationForm()

    return render(request, "booking/signup.html", {"form": form})


# ----------------------------
# Booking Page
# ----------------------------
@login_required
def booking_page(request):
    services = Service.objects.all()
    staff = Staff.objects.all()
    return render(request, "booking/home.html", {
        "services": services,
        "staff": staff
    })


# ----------------------------
# Create Booking
# ----------------------------
@login_required
def create_booking(request):
    staff_id = request.GET.get("staff_id")
    service_id = request.GET.get("service_id")
    date_str = request.GET.get("date")
    start_time = request.GET.get("start")

    if not all([staff_id, service_id, date_str, start_time]):
        messages.error(request, "Invalid booking request.")
        return redirect("booking_page")

    staff = get_object_or_404(Staff, id=staff_id)
    service = get_object_or_404(Service, id=service_id)

    naive_start = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
    start_datetime = timezone.make_aware(naive_start)

    end_datetime = start_datetime + timedelta(minutes=service.duration_minutes)

    # Prevent past booking
    if start_datetime < timezone.now():
        messages.error(request, "You cannot book in the past.")
        return redirect("booking_page")

    # Prevent double booking
    conflict = Booking.objects.filter(
        staff=staff,
        start_datetime__lt=end_datetime,
        end_datetime__gt=start_datetime,
        status__in=["BOOKED", "PENDING_PAYMENT"]
    ).exists()

    if conflict:
        messages.error(request, "This slot is already booked.")
        return redirect("booking_page")

    booking = Booking.objects.create(
        user=request.user,
        staff=staff,
        service=service,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        status="PENDING_PAYMENT",
        is_paid=False
    )

    messages.success(request, "Booking created. Please complete payment.")
    return redirect("fake_payment", booking_id=booking.id)


# ----------------------------
# Dashboard
# ----------------------------
@login_required
def dashboard(request):
    bookings = Booking.objects.filter(user=request.user)

    for booking in bookings:
        if booking.status == "BOOKED" and booking.start_datetime < timezone.now():
            booking.status = "COMPLETED"
            booking.save()

    bookings = bookings.order_by("-start_datetime")

    return render(request, "booking/dashboard.html", {
        "bookings": bookings
    })


# ----------------------------
# Check Availability
# ----------------------------
@login_required
def check_availability(request):
    staff_id = request.GET.get("staff_id")
    service_id = request.GET.get("service_id")
    date_str = request.GET.get("date")

    if not staff_id or not service_id or not date_str:
        messages.error(request, "Missing availability parameters.")
        return redirect("booking_page")

    staff = get_object_or_404(Staff, id=staff_id)
    service = get_object_or_404(Service, id=service_id)

    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Prevent past dates
    if selected_date < timezone.now().date():
        messages.error(request, "Cannot check availability for past dates.")
        return redirect("booking_page")

    day_of_week = selected_date.weekday()

    working_hour = WorkingHour.objects.filter(
        staff=staff,
        day_of_week=day_of_week
    ).first()

    if not working_hour:
        return render(request, "booking/availability.html", {
            "slots": [],
            "staff_id": staff_id,
            "service_id": service_id,
            "date": date_str
        })

    # Working hours as timezone-aware datetimes
    working_start = timezone.make_aware(
        datetime.combine(selected_date, working_hour.start_time)
    )
    working_end = timezone.make_aware(
        datetime.combine(selected_date, working_hour.end_time)
    )

    # Include both booked and pending-payment slots
    existing_bookings = Booking.objects.filter(
        staff=staff,
        start_datetime__date=selected_date,
        status__in=["BOOKED", "PENDING_PAYMENT"]
    )

    breaks = Break.objects.filter(
        staff=staff,
        day_of_week=day_of_week
    )

    engine = SchedulingEngine(
        working_start,
        working_end,
        service.duration_minutes,
        existing_bookings,
        breaks
    )

    slots = engine.generate_slots()

    # Remove past time slots for today
    now = timezone.now()
    slots = [(start, end) for start, end in slots if start > now]

    # Convert UTC-aware slots to local time for display
    formatted_slots = [
        {
            "start": timezone.localtime(slot[0]).strftime("%H:%M"),
            "end": timezone.localtime(slot[1]).strftime("%H:%M")
        }
        for slot in slots
    ]

    return render(request, "booking/availability.html", {
        "slots": formatted_slots,
        "staff_id": staff_id,
        "service_id": service_id,
        "date": date_str
    })


# ----------------------------
# Cancel Booking
# ----------------------------
@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    if booking.status == "BOOKED":
        booking.status = "CANCELLED"
        booking.save()
        messages.success(request, "Booking cancelled successfully.")
    else:
        messages.error(request, "Booking cannot be cancelled.")

    return redirect("dashboard")


# ----------------------------
# Add Review
# ----------------------------
@login_required
def add_review(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user,
        status="COMPLETED"
    )

    if hasattr(booking, "review"):
        messages.error(request, "You already reviewed this booking.")
        return redirect("dashboard")

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.staff = booking.staff
            review.user = request.user
            review.save()
            messages.success(request, "Review submitted!")
            return redirect("dashboard")
    else:
        form = ReviewForm()

    return render(request, "booking/add_review.html", {
        "form": form
    })


# ----------------------------
# Admin Dashboard
# ----------------------------
@staff_member_required
def admin_dashboard(request):
    total_bookings = Booking.objects.count()
    total_revenue = Booking.objects.filter(
        status="COMPLETED"
    ).aggregate(Sum("service__price"))["service__price__sum"] or 0

    bookings_per_staff = (
        Booking.objects.values("staff__name")
        .annotate(total=Count("id"))
    )

    return render(request, "booking/admin_dashboard.html", {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "bookings_per_staff": bookings_per_staff
    })


# ----------------------------
# Reschedule Booking
# ----------------------------
@login_required
def reschedule_booking(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    if request.method == "POST":
        new_date = request.POST.get("date")
        new_time = request.POST.get("time")

        naive_start = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
        start_datetime = timezone.make_aware(naive_start)

        end_datetime = start_datetime + timedelta(
            minutes=booking.service.duration_minutes
        )

        booking.start_datetime = start_datetime
        booking.end_datetime = end_datetime
        booking.save()

        messages.success(request, "Booking rescheduled!")
        return redirect("dashboard")

    return render(request, "booking/reschedule.html", {
        "booking": booking
    })


# ----------------------------
# Fake Payment
# ----------------------------
@login_required
def fake_payment(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    return render(request, "booking/fake_payment.html", {
        "booking": booking
    })


# ----------------------------
# Confirm Payment
# ----------------------------
@login_required
def confirm_payment(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    booking.is_paid = True
    booking.status = "BOOKED"
    booking.save()

    if request.user.email:
        send_mail(
            subject="Payment Successful - CloudBooking",
            message=f"""
Hi {request.user.username},

Your payment has been received.

Service: {booking.service.name}
Date: {timezone.localtime(booking.start_datetime).strftime('%Y-%m-%d')}
Time: {timezone.localtime(booking.start_datetime).strftime('%H:%M')}
""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[request.user.email],
            fail_silently=True,
        )

    messages.success(request, "Payment confirmed successfully!")
    return redirect("dashboard")