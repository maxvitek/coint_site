from django.db import models
from tempodb import TempoDB, pdseries2tdbseries
import datetime
from intradata import get_google_data
from celery.contrib.methods import task_method
from coint_site.celery import app
import logging

logger = logging.getLogger(__name__)


class Company(models.Model):
    name = models.CharField(max_length=150)
    symbol = models.CharField(primary_key=True, max_length=20)
    hq = models.CharField(max_length=150)
    industry = models.CharField(max_length=150)
    sector = models.CharField(max_length=150)
    tempodb = models.IntegerField()

    def get_prices(self):
        logger.info('Fetching prices for: ' + self.symbol)
        tdb = TempoDB()
        self.prices = tdb.db[self.tempodb].read_key(
            self.symbol,
            datetime.datetime(2000, 1, 1, 1, 1, 1),
            datetime.datetime.now(),
            interval='1min')
        return self.prices

    @app.task(filter=task_method)
    def update_prices(self):
        logger.info('Updating prices for: ' + self.symbol)
        tdb = TempoDB()
        df = get_google_data(self.symbol, lookback=15)
        series = df['close']
        tbd_series = pdseries2tdbseries(series)
        tdb.db[self.tempodb].write_key(self.symbol, tbd_series)
        return None


class Pair(models.Model):
    symbol = models.CharField(primary_key=True, max_length=40)
    adf_stat = models.FloatField(null=True)
    adf_p = models.FloatField(null=True)
    adf_1pct = models.FloatField(null=True)
    adf_5pct = models.FloatField(null=True)
    adf_10pct = models.FloatField(null=True)

    def component_tickers(self):
        return self.symbol.split('-')