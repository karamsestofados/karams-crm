from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    description: str
    start_date: date
    start_time: time
    location: str = ''
    duration_minutes: int = 60

    @property
    def start_datetime(self) -> datetime:
        return datetime.combine(self.start_date, self.start_time)

    @property
    def end_datetime(self) -> datetime:
        from datetime import timedelta

        return self.start_datetime + timedelta(minutes=self.duration_minutes)
