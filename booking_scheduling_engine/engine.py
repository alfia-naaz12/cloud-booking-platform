from datetime import timedelta
from .conflict import ConflictDetector
from .rules import RuleEngine


class SchedulingEngine:
    """
    SchedulingEngine is responsible for generating valid
    appointment slots for a given staff member on a specific date.

    It considers:
    - Working hours
    - Service duration
    - Existing bookings
    - Break timings
    """
    def __init__(self, working_start, working_end, service_duration, existing_bookings, breaks):
        """
        Constructor method.

        working_start: datetime when staff starts working
        working_end: datetime when staff stops working
        service_duration: duration of selected service in minutes
        existing_bookings: list/queryset of current bookings
        breaks: list/queryset of break times
        """

        self.working_start = working_start
        self.working_end = working_end
        self.service_duration = service_duration
         # Create conflict detector instance
        self.conflict_detector = ConflictDetector(existing_bookings)
        # Create rule engine instance (for break checking)
        self.rule_engine = RuleEngine(breaks)

    def generate_slots(self):
        """
        Generates all available time slots.

        Returns:
            List of tuples -> [(start_time, end_time), ...]
        """
        slots = []
         # Start from the beginning of working hours
        current_time = self.working_start
        # Continue until next slot exceeds working end time

        while current_time + timedelta(minutes=self.service_duration) <= self.working_end:
            # Calculate slot end time
            end_time = current_time + timedelta(minutes=self.service_duration)
            # Step 1: Check if this slot conflicts with existing bookings
            if not self.conflict_detector.has_conflict(current_time, end_time):
                # Step 2: Check if this slot overlaps with break time
                if not self.rule_engine.is_within_break(current_time, end_time):
                    # If no conflict and not during break → slot is valid
                    slots.append((current_time, end_time))
                # Move to next possible slot
            current_time += timedelta(minutes=self.service_duration)

        return slots