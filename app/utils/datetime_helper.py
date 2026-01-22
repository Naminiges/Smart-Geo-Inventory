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
    Format datetime to WIB (GMT+7) string
    Converts from UTC to WIB if needed
    """
    if dt is None:
        return '-'

    # Convert to WIB
    if dt.tzinfo is not None:
        # Already timezone-aware, convert to WIB
        wib_dt = dt.astimezone(WIB)
    else:
        # Naive datetime, assume it's UTC and convert to WIB
        utc_dt = dt.replace(tzinfo=timezone.utc)
        wib_dt = utc_dt.astimezone(WIB)

    # Return as naive datetime string (without timezone info)
    return wib_dt.replace(tzinfo=None).strftime(format_str)
