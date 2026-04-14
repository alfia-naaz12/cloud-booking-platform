from django.urls import path
from . import views

urlpatterns = [
    # Landing page
    path("", views.home, name="home"),

    # Booking form page (requires login)
    path("book-appointment/", views.booking_page, name="booking_page"),

    # Availability checker
    path("availability/", views.check_availability, name="availability"),

    # Create booking after clicking slot
    path("book/", views.create_booking, name="book"),

    # User dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Signup
    path("signup/", views.register, name="signup"),
    
    #cancel
    path("cancel/<int:booking_id>/", views.cancel_booking, name="cancel_booking"),
    
    path("payment/<int:booking_id>/", views.fake_payment, name="fake_payment"),
    path("confirm-payment/<int:booking_id>/", views.confirm_payment, name="confirm_payment"),
    path("review/<int:booking_id>/", views.add_review, name="add_review"),
]