from datetime import datetime
from urllib.parse import urlencode

from .event import CalendarEvent

GOOGLE_CALENDAR_TEMPLATE_URL = 'https://calendar.google.com/calendar/render'


def _format_google_datetime(dt: datetime) -> str:
    return dt.strftime('%Y%m%dT%H%M%S')


def build_google_calendar_url(event: CalendarEvent) -> str:
    dates = (
        f'{_format_google_datetime(event.start_datetime)}/'
        f'{_format_google_datetime(event.end_datetime)}'
    )
    params = {
        'action': 'TEMPLATE',
        'text': event.title,
        'details': event.description,
        'dates': dates,
    }
    if event.location:
        params['location'] = event.location
    return f'{GOOGLE_CALENDAR_TEMPLATE_URL}?{urlencode(params)}'
