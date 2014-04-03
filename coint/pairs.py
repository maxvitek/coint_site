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
from termcolor import colored

logger = logging.getLogger(__name__)


class PairAnalysis(object):
    """

    """
    def __init__(self, c1, c2, lookback=1000):
        self.companies = []

        self.companies.append(self.get_company(c1))
        self.companies.append(self.get_company(c2))
        self.df_dict = {}

        company_num = 1
        for c in self.companies:
            if not hasattr(c, 'prices'):
                c.get_raw_prices(lookback=lookback)
            self.df_dict['company_' + str(company_num)] = c.prices
            company_num += 1

        sym1, sym2 = sorted([c.symbol for c in self.companies])
        self.symbol = sym1 + '-' + sym2

        logger.info(self.symbol + '::Conducting pair analysis: ' + self.symbol)

        self.adf = None
        self.ols = None
        self.df = pd.DataFrame(self.df_dict)
        self.pair, self.created = Pair.objects.get_or_create(
            symbol=self.symbol,
        )

        self.analyze()

        if self.pair.adf_stat < self.pair.adf_5pct:
            coint_log_item = colored('Cointegrated', 'green', attrs=['bold'])
        else:
            coint_log_item = colored('Not Cointegrated', 'red', attrs=['bold'])

        logger.info(self.symbol + '::' + coint_log_item + ': ' + str(self.pair.adf_stat))

    def get_company(self, co_arg):
        if isinstance(co_arg, str) or isinstance(co_arg, unicode):
            company = Company.objects.filter(symbol=co_arg).get()
        elif isinstance(co_arg, Company):
            company = co_arg
        else:
            raise ValueError
        return company

    def analyze(self):
        logger.info(self.symbol + '::Conducting analysis')

        company_num = 1
        for c in self.companies:
            c.log_prices = np.log(c.prices)
            self.df['log_company_' + str(company_num)] = c.log_prices
            company_num += 1
        self.df.dropna().interpolate()
        self.ols, self.adf = engle_granger_test(y=self.df['log_company_1'], x=self.df['log_company_2'])
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


def engle_granger_test(y, x):
    ols_res = ols(y=y, x=x, intercept=False)
    adf_res = ts.adfuller(ols_res.resid)
    return ols_res, adf_res


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


def make_pairs_csv(pairs=None, threshold=100):
    """
    This makes a csv file in the project
    """
    if not pairs:
        pairs = Pair.objects.all()

    companies = Company.objects.all()
    industries = {}
    sectors = {}
    for c in companies:
        industries[c.symbol] = c.industry
        sectors[c.symbol] = c.sector

    filepath = os.path.join(os.getcwd(), 'coint', 'static', 'pairs_' + str(threshold) + '.csv')
    with open(filepath, 'w') as f:
        c = csv.writer(f)
        c.writerow(['symbol', 'symbol_1', 'symbol_2', 'adf_stat', 'adf_p',
                    'industry_1', 'industry_2', 'sector_1', 'sector_2'])
        sorted_pairs = sorted(pairs, key=lambda x: x.adf_p)
        short_pairs = sorted_pairs[:int(len(pairs) * threshold / 100) - 1]
        for p in short_pairs:
            row_data = p.csv_data()
            c.writerow(row_data + [industries[row_data[1]], industries[row_data[2]],
                                   sectors[row_data[1]], sectors[row_data[2]]])

    return None
