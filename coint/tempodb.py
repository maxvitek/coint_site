from __future__ import absolute_import
from tempodb import Client as TempoDBClient
from coint_site.settings import TEMPODB


class TempoDB(object):
    """
    Abstract Coint's interactions with the
    TempoDB service, esp free tier
    """
    TEMPODB_FREE_SERIES = 50

    def __init__(self):
        self.num = len(TEMPODB)
        self.db = {}
        for i in TEMPODB:
            self.db[i] = TempoDBClient(
                TEMPODB[i]['KEY'],
                TEMPODB[i]['SECRET'],
                host=TEMPODB[i]['HOST'],
                port=TEMPODB[i]['PORT'],
            )

    def get_mapping(self, series_list):
        """
        Take a list of series, and provide a mapping
        to tempodb instance
        :param series_list: list
        :param tempodb_num: int
        :return mapping: dictionary
        """
        if len(series_list) > self.num * self.TEMPODB_FREE_SERIES:
            raise TooManySeries('Get more TempoDBs.')

        mapping = {}

        i = 1
        j = 0

        for series in series_list:
            mapping[series] = i
            if j == self.TEMPODB_FREE_SERIES:
                i += 1
                j = 0
            else:
                j += 1

        return mapping


class TooManySeries(Exception):
    pass
