class RuleEngine:
    """
    RuleEngine is responsible for validating time slots
    against business rules such as staff breaks.

    It ensures appointments are not scheduled during break times.
    """
    def __init__(self, breaks):
        """
        Constructor method.

        breaks:
        A list/queryset of break objects for a staff member
        on a specific day.
        """
        self.breaks = breaks

    def is_within_break(self, start_time, end_time):
        """
        Checks whether the proposed time slot overlaps
        with any defined break period.

        Returns:
            True  -> If slot overlaps with break
            False -> If slot is valid
        """

        for br in self.breaks:
            # Convert datetime to time for comparison
            # We only compare time (not date)
            if start_time.time() < br.end_time and end_time.time() > br.start_time:
                return True # Slot overlaps with break
        return False  # Slot overlaps with break