"""
Datetime helper functions for timezone handling
"""
from datetime import datetime, timezone, timedelta


# GMT+7 timezone (WIB - Waktu Indonesia Barat)
WIB = timezone(timedelta(hours=7))


def get_wib_now():
    """
    Get current time in GMT+7 (WIB)
    Returns timezone-aware datetime object
    """
    return datetime.now(WIB)


def utc_to_wib(utc_datetime):
    """
    Convert UTC datetime to WIB (GMT+7)
    """
    if utc_datetime is None:
        return None

    # If already timezone-aware, convert to WIB
    if utc_datetime.tzinfo is not None:
        return utc_datetime.astimezone(WIB)

    # If naive, assume it's UTC and add timezone
    utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    return utc_datetime.astimezone(WIB)


def format_wib_datetime(dt, format_str='%d/%m/%Y - %H:%M'):
    """
    Format datetime to string (assumes already in WIB)
    """
    if dt is None:
        return '-'

    # If timezone-aware, convert to naive WIB
    if dt.tzinfo is not None:
        wib_dt = dt.astimezone(WIB).replace(tzinfo=None)
    else:
        # Assume already in WIB and naive
        wib_dt = dt

    return wib_dt.strftime(format_str)
