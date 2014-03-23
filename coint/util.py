import time
from finsymbols import get_sp500_symbols
from tempodb import TempoDB
from models import Company


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
        company = Company.objects.create(

        )