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

logger = logging.getLogger(__name__)


class PairAnalysis(object):
    """

    """
    def __init__(self, ticker1, ticker2):
        logger.info(ticker1 + ticker2 + '::Conducting pair analysis: ' + ticker1 + ' & ' + ticker2)
        self.tdb = TempoDB()
        sym1, sym2 = sorted([ticker1, ticker2])
        self.symbol = sym1 + '-' + sym2
        self.s1 = Company.objects.filter(symbol=sym1).get()
        self.s2 = Company.objects.filter(symbol=sym2).get()
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
        logger.info(self.symbol + '::Getting prices')
        data1 = tdbseries2pdseries(self.s1.get_prices())
        data2 = tdbseries2pdseries(self.s2.get_prices())
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
    df = pd.DataFrame({ticker1: df1['close'], ticker2: df2['close']}).interpolate()
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
    symbols = sorted([co.symbol for co in companies])
    combos = [i for i in itertools.combinations(symbols, 2)]

    for c in combos:
        ticker1 = c[0]
        ticker2 = c[1]
        make_pair.delay(ticker1, ticker2)

    return
