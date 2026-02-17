from icalendar import Calendar, Event
from datetime import datetime

def generate_ics_file(tasks):
    # Initialize the Calendar
    cal = Calendar()
    cal.add('prodid', '-//ScheduleSmart Pro//mxm.dk//')
    cal.add('version', '2.0')

    for t in tasks:
        # Create an event
        event = Event()
        event.add('summary', t['name'])

        # Handle Start Time
        start = t.get('start_time')
        if start:
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            event.add('dtstart', start)

        # Handle End Time
        end = t.get('end_time')
        if end:
            if isinstance(end, str):
                end = datetime.fromisoformat(end)
            event.add('dtend', end)

        # Add Notes
        if t.get('notes'):
            event.add('description', t['notes'])

        # Add to Calendar
        cal.add_component(event)

    return cal.to_ical()