"""
Calendar Service (.ics file generator) using icalendar.
Conforms to strict ₹0 baseline: zero-cost local RFC 5545 calendar export.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from icalendar import Calendar, Event, Alarm
from app.models import Deadline, Reminder


def generate_ics_content(deadline: Deadline, reminders: Optional[List[Reminder]] = None) -> str:
    """
    Generate RFC 5545 compliant iCalendar string for a deadline obligation,
    including advance alarms for all scheduled reminders.
    """
    cal = Calendar()
    cal.add('prodid', '-//Aheadly//Deadline Rescue//Alexa+ Hackathon 2026//EN')
    cal.add('version', '2.0')

    if not deadline.candidate_date or deadline.candidate_date == "UNVERIFIED":
        raise ValueError(f"Cannot generate calendar export for unverified deadline obligation '{deadline.id}'.")

    # Parse candidate date
    try:
        dt = datetime.fromisoformat(deadline.candidate_date.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(deadline.candidate_date[:10], "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid deadline date format '{deadline.candidate_date}' for calendar export.")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    event = Event()
    event.add('summary', f"[Aheadly] {deadline.provider_name} - {deadline.obligation_type.value.replace('_', ' ').title()}")
    event.add('dtstart', dt)
    event.add('dtend', dt + timedelta(hours=1))
    event.add('dtstamp', datetime.now(timezone.utc))
    event.add('uid', f"deadline-{deadline.id}@deadlinerescue.local")

    desc_lines = [
        f"Provider: {deadline.provider_name}",
        f"Obligation: {deadline.obligation_type.value}",
        f"Evidence: \"{deadline.evidence_snippet}\"",
    ]
    if deadline.amount:
        desc_lines.append(f"Amount: {deadline.currency} {deadline.amount:,.2f}")
    if deadline.official_url:
        desc_lines.append(f"Action Link: {deadline.official_url}")
    if deadline.next_step_instructions:
        desc_lines.append(f"Instructions: {deadline.next_step_instructions}")

    event.add('description', "\n".join(desc_lines))

    # Add reminders as iCalendar ALARMs
    if reminders:
        for rem in reminders:
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', f"Reminder: {deadline.provider_name} obligation is due in {rem.lead_days} days.")
            alarm.add('trigger', timedelta(days=-rem.lead_days))
            event.add_component(alarm)
    else:
        # Default alarm: 1 day before
        alarm = Alarm()
        alarm.add('action', 'DISPLAY')
        alarm.add('description', f"Reminder: {deadline.provider_name} obligation due tomorrow.")
        alarm.add('trigger', timedelta(days=-1))
        event.add_component(alarm)

    cal.add_component(event)
    return cal.to_ical().decode("utf-8")
