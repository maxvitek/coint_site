from intradata import get_google_data
from finsymbols import get_sp500_symbols
import pandas as pd
from pandas.stats.api import ols
import statsmodels.tsa.stattools as ts
import numpy as np
from util import timestamp
import logging
from coint_site.celery import app
import itertools
from tempodb import TempoDB, tdbseries2pdseries
from models import Company, Pair
from threadpool import ThreadPool
import csv
import os

logger = logging.getLogger(__name__)


class PairAnalysis(object):
    """

    """
    def __init__(self, c1, c2):

        if isinstance(c1, str):
            self.s1 = Company.objects.filter(symbol=c1).get()
        elif isinstance(c1, Company):
            self.s1 = c1
            if not self.s1.prices:
                logger.info(self.s1.symbol + '::Getting prices')
                self.s1.get_prices()
        else:
            raise ValueError

        if isinstance(c2, str):
            self.s2 = Company.objects.filter(symbol=c2).get()
        elif isinstance(c2, Company):
            self.s2 = c2
            if not self.s2.prices:
                logger.info(self.s2.symbol + '::Getting prices')
                self.s2.get_prices()
        else:
            raise ValueError

        sym1, sym2 = sorted([c1.symbol, c2.symbol])
        self.symbol = sym1 + '-' + sym2
        logger.info(self.symbol + '::Conducting pair analysis: ' + c1.symbol + ' & ' + c2.symbol)
        self.tdb = TempoDB()
        self.adf = None
        self.ols = None
        self.pair, self.created = Pair.objects.get_or_create(
            symbol=self.symbol,
        )

        self.analyze()

        self.persist()

        if self.pair.adf_stat < self.pair.adf_1pct:
            logger.info(self.symbol + '::Cointegrated: ' + str(self.pair.adf_stat))
        if not self.pair.adf_stat < self.pair.adf_1pct:
            logger.info(self.symbol + '::Not Cointegrated: ' + str(self.pair.adf_stat))

    def analyze(self):
        logger.info(self.symbol + '::Conducting analysis    ')
        data1 = tdbseries2pdseries(self.s1.prices)
        data2 = tdbseries2pdseries(self.s2.prices)
        logdata1 = np.log(data1).dropna()
        logdata2 = np.log(data2).dropna()
        self.ols = ols(y=logdata1, x=logdata2)
        self.adf = ts.adfuller(self.ols.resid)

    def persist(self):
        logger.info(self.symbol + '::Persisting analysis')
        self.pair.adf_stat = self.adf[0]
        self.pair.adf_p = self.adf[1]
        self.pair.adf_1pct = self.adf[4]['1%']
        self.pair.adf_5pct = self.adf[4]['5%']
        self.pair.adf_10pct = self.adf[4]['10%']
        self.pair.save()


def get_pair(ticker1, ticker2, data_frame_result=False, lookback=1):
    """
    We take two tickers and return either
    a pandas dataframe or a list of dicts
    depending on 'data_frame_result' kwarg
    :params ticker1: str
    :params ticker2: str
    :return DataFrame, list (of dicts)
    """
    df1 = get_google_data(ticker1, lookback=lookback)
    df2 = get_google_data(ticker2, lookback=lookback)
    df = pd.DataFrame({ticker1: df1['close'], ticker2: df2['close']}).dropna().interpolate()
    if data_frame_result:
        logger.info('pairs dataframe returned for ' + ticker1 + ' and ' + ticker2)
        return df

    pair_data = []
    for t in df.iterrows():
        pair_data.append({
            'datetime': timestamp(t[0]),
            'ticker1': t[1][ticker1],
            'ticker2': t[1][ticker2],
        })
    logger.info('pairs data list returned for ' + ticker1 + ' and ' + ticker2)
    return pair_data


@app.task
def get_adf(ticker1, ticker2):
    """

    """
    df = get_pair(ticker1, ticker2, data_frame_result=True, lookback=15)
    ln_df = np.log(df).dropna()
    reg = ols(y=ln_df[ticker1], x=ln_df[ticker2])
    result = ts.adfuller(reg.resid)
    return result


def test_all_pairs():
    symbols = sorted([s['symbol'] for s in get_sp500_symbols()])[:3]
    combs = [i for i in itertools.combinations(symbols, 2)]
    results = []
    for c in combs:
        ticker1 = c[0]
        ticker2 = c[1]
        adf = get_adf.delay(ticker1, ticker2)
        results.append((c, adf))

    return sorted(results, key=lambda x: x[1][0])


def seed():
    """
    This will seed the dbs with everything we need
    """
    sp500 = get_sp500_symbols()
    symbols = [s['symbol'] for s in sp500]
    tempodb = TempoDB()
    tempodb_mapping = tempodb.get_mapping(symbols)

    for co in sp500:
        logger.info('Seeding: ' + co['symbol'])
        company = Company.objects.create(
            name=co['company'],
            symbol=co['symbol'],
            hq=co['headquarters'],
            industry=co['industry'],
            sector=co['sector'],
            tempodb=tempodb_mapping[co['symbol']]
        )

        company.update_prices.delay()

        company.save()

    return

@app.task
def make_pair(ticker1, ticker2):
    """
    A function which makes a PairAnalysis object
    used farm off the task to a celery worker
    """
    PairAnalysis(ticker1, ticker2)
    return


def make_all_pairs():
    """
    This will check all of the pairs
    """
    companies = Company.objects.all()
    tpool = ThreadPool(50)
    for c in companies:
        tpool.add_task(c.get_prices)
    tpool.wait_completion()

    for c in itertools.combinations(companies, 2):
        c1 = c[0]
        c2 = c[1]
        tpool.add_task(make_pair, c1, c2)
    tpool.wait_completion()

    return


def make_pairs_csv():
    """
    This makes a csv file in the project
    """
    filepath = os.path.join(os.getcwd(), 'coint', 'static', 'pairs.csv')
    with open(filepath, 'w') as f:
        c = csv.writer(f)
        c.writerow(['symbol', 'symbol_1', 'symbol_2', 'adf_stat', 'adf_p'])
        pairs = Pair.objects.all()
        for p in pairs:
            c.writerow(p.csv_data())
