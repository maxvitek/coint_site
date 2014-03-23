import time
from finsymbols import get_sp500_symbols
from tempodb import TempoDB
from models import Company
from pandas import Series


def timestamp(date_time):
    """
    Return POSIX timestamp as float
    """
    return time.mktime((date_time.year, date_time.month, date_time.day,
                        date_time.hour, date_time.minute, date_time.second,
                        -1, -1, -1)) + date_time.microsecond / 1e6


def seed():
    """
    This will seed the dbs with everything we need
    """
    sp500 = get_sp500_symbols()
    symbols = [s['symbol'] for s in sp500]
    tempodb = TempoDB()
    tempodb_mapping = tempodb.get_mapping(symbols)

    for co in sp500:
        Company.objects.create(
            name=co['company'],
            symbol=co['symbol'],
            hq=co['headquarters'],
            industry=co['industry'],
            sector=co['sector'],
            tempodb=tempodb_mapping[co['symbol']]
        ).save()

    return


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