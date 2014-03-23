import time
from pandas import Series


def timestamp(date_time):
    """
    Return POSIX timestamp as float
    """
    return time.mktime((date_time.year, date_time.month, date_time.day,
                        date_time.hour, date_time.minute, date_time.second,
                        -1, -1, -1)) + date_time.microsecond / 1e6


def series2js(pd_series):
    """
    Converts pandas Series object to something
    more friendly to display in d3.js
    """
    if not isinstance(pd_series, Series):
        raise NotATimeSeries()
    data = []
    for t in pd_series.iteritems():
        data.append({
            'datetime': timestamp(t[0]),
            'price': t[1],
        })


class NotATimeSeries(Exception):
    pass