from datetime import datetime, date, timedelta


def get_week_bounds(target_date: date | None = None) -> tuple[date, date]:
    target = target_date or date.today()
    week_start = target - timedelta(days=target.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def format_date(d: date | datetime) -> str:
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d %H:%M")
    return d.strftime("%Y-%m-%d")


def days_until(target: date) -> int:
    return (target - date.today()).days


def is_today(d: date) -> bool:
    return d == date.today()


def is_overdue(deadline: date) -> bool:
    return deadline < date.today()