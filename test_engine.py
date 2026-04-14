from datetime import datetime
from booking_scheduling_engine.engine import SchedulingEngine

working_start = datetime(2026, 3, 1, 9, 0)
working_end = datetime(2026, 3, 1, 12, 0)
service_duration = 30

existing_bookings = []
breaks = []

engine = SchedulingEngine(
    working_start,
    working_end,
    service_duration,
    existing_bookings,
    breaks
)

slots = engine.generate_slots()

for s in slots:
    print(s)