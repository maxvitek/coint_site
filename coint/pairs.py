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
    def __init__(self, c1, c2, update_lookback=15, lookback=1000):

        if isinstance(c1, str) or isinstance(c1, unicode):
            self.s1 = Company.objects.filter(symbol=c1).get()
        elif isinstance(c1, Company):
            self.s1 = c1
        else:
            raise ValueError

        if isinstance(c2, str) or isinstance(c2, unicode):
            self.s2 = Company.objects.filter(symbol=c2).get()
        elif isinstance(c2, Company):
            self.s2 = c2
        else:
            raise ValueError

        if not hasattr(self.s1, 'prices') and not hasattr(self.s2, 'prices'):
            self.s1.update_prices(lookback=update_lookback)
            self.s2.update_prices(lookback=update_lookback)
            self.s1.get_prices(lookback=lookback)
            self.s2.get_prices(lookback=lookback)

        if not hasattr(self.s1, 'prices'):
            self.s1.update_prices(lookback=update_lookback)
            self.s1.get_prices(lookback=lookback)

        if not hasattr(self.s2, 'prices'):
            self.s2.update_prices(lookback=update_lookback)
            self.s2.get_prices(lookback=lookback)

        sym1, sym2 = sorted([self.s1.symbol, self.s2.symbol])
        self.symbol = sym1 + '-' + sym2
        logger.info(self.symbol + '::Conducting pair analysis: ' + self.s1.symbol + ' & ' + self.s2.symbol)
        self.tdb = TempoDB()
        self.data1 = None
        self.data2 = None
        self.log_data1 = None
        self.log_data2 = None
        self.adf = None
        self.ols = None
        self.view_data = None
        self.pair, self.created = Pair.objects.get_or_create(
            symbol=self.symbol,
        )

        self.analyze()

        if self.pair.adf_stat < self.pair.adf_1pct:
            logger.info(self.symbol + '::Cointegrated: ' + str(self.pair.adf_stat))
        if not self.pair.adf_stat < self.pair.adf_1pct:
            logger.info(self.symbol + '::Not Cointegrated: ' + str(self.pair.adf_stat))

    def analyze(self):
        logger.info(self.symbol + '::Conducting analysis')
        self.data1 = tdbseries2pdseries(self.s1.prices)
        self.data2 = tdbseries2pdseries(self.s2.prices)
        self.log_data1 = np.log(self.data1).dropna()
        self.log_data2 = np.log(self.data2).dropna()
        self.ols = ols(y=self.log_data1, x=self.log_data2, intercept=False)
        self.adf = ts.adfuller(self.ols.resid)
        return None

    def persist(self):
        logger.info(self.symbol + '::Persisting analysis')
        self.pair.adf_stat = self.adf[0]
        self.pair.adf_p = self.adf[1]
        self.pair.adf_1pct = self.adf[4]['1%']
        self.pair.adf_5pct = self.adf[4]['5%']
        self.pair.adf_10pct = self.adf[4]['10%']
        self.pair.save()
        return None

    def get_view_data(self):
        df = pd.DataFrame({
            self.s1.symbol: self.data1,
            self.s2.symbol: self.data2,
            'log_' + self.s1.symbol: self.log_data1,
            'log_' + self.s2.symbol: self.log_data2,
        }).dropna().interpolate()

        pair_data = []
        for t in df.iterrows():
            pair_data.append({
                'datetime': timestamp(t[0]),
                'ticker1': t[1][self.s1.symbol],
                'ticker2': t[1][self.s2.symbol],
                'log_ticker1': t[1]['log_' + self.s1.symbol],
                'log_ticker2': t[1]['log_' + self.s2.symbol],
            })

        resid_data = []
        for t in self.ols.resid.index:
            resid_data.append({
                'datetime': timestamp(t),
                'resid': self.ols.resid[t],
            })

        self.view_data = {
            'pair_data': pair_data,
            'resid_data': resid_data,
            'ols': self.ols,
            'adf': self.adf,
            'company_1': self.s1,
            'company_2': self.s2,
        }
        return self.view_data


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
    df = pd.DataFrame({ticker1: df1['close'], ticker2: df2['close'], 'log_' + ticker1: np.log(df1)['close'],
                       'log_' + ticker2: np.log(df2)['close']}).dropna().interpolate()
    if data_frame_result:
        logger.info('pairs dataframe returned for ' + ticker1 + ' and ' + ticker2)
        return df

    pair_data = []
    for t in df.iterrows():
        pair_data.append({
            'datetime': timestamp(t[0]),
            'ticker1': t[1][ticker1],
            'ticker2': t[1][ticker2],
            'log_ticker1': t[1]['log_' + ticker1],
            'log_ticker2': t[1]['log_' + ticker2],
        })
    logger.info('pairs data list returned for ' + ticker1 + ' and ' + ticker2)
    return pair_data


@app.task
def get_adf(ticker1, ticker2):
    """

    """
    df = get_pair(ticker1, ticker2, data_frame_result=True, lookback=15)
    ln_df = np.log(df).dropna()
    reg = ols(y=ln_df[ticker1], x=ln_df[ticker2], intercept=False)
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
    pa = PairAnalysis(ticker1, ticker2)
    pa.persist()
    return


def make_all_pairs():
    """
    This will check all of the pairs
    """
    logger.info('Collecting companies')
    companies = Company.objects.all()
    tpool = ThreadPool(75)

    logger.info('Updating prices')
    for c in companies:
        tpool.add_task(c.update_prices)
    tpool.wait_completion()

    logger.info('Fetching full price histories')
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
    companies = Company.objects.all()
    industries = {}
    sectors = {}
    for c in companies:
        industries[c.symbol] = c.industry
        sectors[c.symbol] = c.sector

    filepath = os.path.join(os.getcwd(), 'coint', 'static', 'pairs.csv')
    with open(filepath, 'w') as f:
        c = csv.writer(f)
        c.writerow(['symbol', 'symbol_1', 'symbol_2', 'adf_stat', 'adf_p',
                    'industry_1', 'industry_2', 'sector_1', 'sector_2'])
        pairs = Pair.objects.all()
        for p in pairs:
            row_data = p.csv_data()
            c.writerow(row_data + [industries[row_data[1]], industries[row_data[2]],
                                   sectors[row_data[1]], sectors[row_data[2]]])
