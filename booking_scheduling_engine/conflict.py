from django.utils import timezone

class ConflictDetector:
    def __init__(self, existing_bookings):
        self.existing_bookings = existing_bookings

    def has_conflict(self, start_time, end_time):

        # ✅ FIX: ensure slot times are timezone-aware
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)

        if timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)

        for booking in self.existing_bookings:

            booking_start = booking.start_datetime
            booking_end = booking.end_datetime

            # ✅ EXTRA SAFETY (in case DB has naive values)
            if timezone.is_naive(booking_start):
                booking_start = timezone.make_aware(booking_start)

            if timezone.is_naive(booking_end):
                booking_end = timezone.make_aware(booking_end)

            if start_time < booking_end and end_time > booking_start:
                return True

        return False