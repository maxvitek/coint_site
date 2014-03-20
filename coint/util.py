import time


def timestamp(date_time):
    """
    Return POSIX timestamp as float
    """
    return time.mktime((date_time.year, date_time.month, date_time.day,
                        date_time.hour, date_time.minute, date_time.second,
                        -1, -1, -1)) + date_time.microsecond / 1e6