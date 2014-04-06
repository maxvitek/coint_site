from django.db import models
from tempodb import TempoDB, pdseries2tdbseries, tdbseries2pdseries
import datetime
from intradata import get_google_data
from celery.contrib.methods import task_method
from coint_site.celery import app
import logging
from djangotoolbox.fields import ListField
import numpy as np

logger = logging.getLogger(__name__)


class Company(models.Model):
    name = models.CharField(max_length=150)
    symbol = models.CharField(primary_key=True, max_length=20)
    hq = models.CharField(max_length=150)
    industry = models.CharField(max_length=150)
    sector = models.CharField(max_length=150)
    tempodb = models.IntegerField()

    def get_prices(self, lookback=1000):
        tdb = TempoDB()
        start_time = datetime.datetime.now() - datetime.timedelta(days=lookback - 1)
        # our start time should actually be the next midnight
        # (so a lookback of 1 is just today's trading day, not any of yesterday's data)
        start = datetime.datetime(start_time.year, start_time.month, start_time.day, 0, 0, 0)
        end = datetime.datetime.now()
        logger.info('Fetching prices for: ' + self.symbol + ' from ' + str(start) + ' to ' + str(end))
        prices = tdb.db[self.tempodb].read_key(
            self.symbol,
            start,
            end,
            interval='1min')
        self.prices = tdbseries2pdseries(prices)
        return self.prices

    @app.task(filter=task_method)
    def update_prices(self, lookback=15):
        logger.info('Updating prices for: ' + self.symbol)
        tdb = TempoDB()
        series = self.get_raw_prices(lookback=lookback)
        tbd_series = pdseries2tdbseries(series)
        tdb.db[self.tempodb].write_key(self.symbol, tbd_series)
        return None

    def get_raw_prices(self, lookback=15):
        df = get_google_data(self.symbol, lookback=lookback)
        series = df['close']
        self.prices = series
        return self.prices

    def get_volumes(self, lookback=15):
	df = get_google_data(self.symbol, lookback=lookback)
	series = df['volume']
	self.volumes = series
	return self.volumes


class Pair(models.Model):
    symbol = models.CharField(primary_key=True, max_length=40)
    adf_p = ListField()
    ols_beta = ListField()
    freq = ListField()
    ranking_statistic = models.FloatField(default=0)
    volume = models.FloatField(default=0, null=True)
    updated = models.DateTimeField(auto_now=True, null=True)

    def component_tickers(self):
        return self.symbol.split('-')

    def csv_data(self):
        avg_p_stat = np.mean([a for a in self.adf_p])
        avg_freq = np.mean([f for f in self.freq])
        return [self.symbol] + self.component_tickers() + [self.ranking_statistic, avg_p_stat, avg_freq]
