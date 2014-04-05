import pickle
import csv
import os
import itertools
import logging
import gzip
import subprocess

from finsymbols import get_sp500_symbols
import pandas as pd
from pandas.stats.api import ols
import statsmodels.tsa.stattools as ts
import numpy as np
from termcolor import colored

from coint_site.celery import app
from tempodb import TempoDB
from models import Company, Pair
from threadpool import ThreadPool
from util import clean_str


logger = logging.getLogger(__name__)


class PairAnalysis(object):
    """
    Abstraction of the pair analytics
    """
    Z_SCORE_BUY = 1.5
    Z_SCORE_SELL = 0.5
    Z_SCORE_PANIC = 4
    DECAY_HALFLIFE = 820800

    def __init__(self, c1, c2, lookback=15):
        self.companies = []

        self.companies.append(self.get_company(c1))
        self.companies.append(self.get_company(c2))
        self.df_dict = {}

        company_num = 1
        for c in self.companies:
            if not hasattr(c, 'prices'):
                c.get_raw_prices(lookback=lookback)
            self.df_dict['company_' + str(company_num)] = c.prices
            c.log_prices = np.log(c.prices)  # taking only this date
            self.df_dict['log_company_' + str(company_num)] = c.log_prices
            company_num += 1

        date_span = set([d.date() for d in self.companies[0].prices.index])

        sym1, sym2 = sorted([c.symbol for c in self.companies])
        self.symbol = sym1 + '-' + sym2

        logger.info(self.symbol + '::Conducting pair analysis: ' + self.symbol)

        self.df = pd.DataFrame(self.df_dict).dropna().interpolate()
        self.pair, self.created = Pair.objects.get_or_create(
            symbol=self.symbol,
        )

        self.ranking_statistic = 0

        self.analyses = []

        for d in date_span:
            self.analyze(d)

        self.compute_ranking_statistic()

    def get_company(self, co_arg):
        if isinstance(co_arg, str) or isinstance(co_arg, unicode):
            company = Company.objects.filter(symbol=co_arg).get()
        elif isinstance(co_arg, Company):
            company = co_arg
        else:
            raise ValueError
        return company

    def analyze(self, date):
        logger.debug(self.symbol + '::Conducting analysis')

        ols_res, adf_res = engle_granger_test(
            y=self.df['log_company_1'][str(date)],
            x=self.df['log_company_2'][str(date)]
        )
        res_mean = np.mean(ols_res.resid)
        res_std = np.std(ols_res.resid)
        pos = 0
        successes = 0
        ols_res.z_score = (ols_res.resid - res_mean) / res_std
        for z in ols_res.z_score:
            if abs(z) > self.Z_SCORE_BUY and not pos:
                pos += 1
            if abs(z) < self.Z_SCORE_SELL and pos:
                pos = 0
                successes += 1
            if abs(z) > self.Z_SCORE_PANIC and pos:
                pos = 0

        self.analyses.append({
            'date': date,
            'ols': ols_res,
            'adf': adf_res,
            'freq': successes
        })

        if adf_res[0] < adf_res[4]['5%']:
            coint_log_item = colored('Cointegrated', 'green', attrs=['bold'])
        else:
            coint_log_item = colored('Not Cointegrated', 'red', attrs=['bold'])

        logger.info(self.symbol + '::' + str(date) + '::' + coint_log_item + '::p-' + str(adf_res[1]) + '::f-' + str(successes))

        return None

    def persist(self):
        logger.info(self.symbol + '::Persisting analysis')
        self.pair.adf_p = [a['adf'][1] for a in self.analyses]
        self.pair.ols_beta = [a['ols'].beta.x for a in self.analyses]
        self.pair.freq = [a['freq'] for a in self.analyses]
        self.pair.ranking_statistic = self.ranking_statistic
        self.pair.save()
        return None

    def compute_ranking_statistic(self):
        """
        This is the magic
        """
        decay_lambda = np.log(2) / self.DECAY_HALFLIFE
        stat = 1
        benchmark_time = self.companies[0].prices.index[-1].date()
        for a in self.analyses:
            t = (benchmark_time - a['date']).total_seconds()
            stat += (1 - a['adf'][1]) * a['freq'] * np.exp(-1 * decay_lambda * t)
        self.ranking_statistic = stat
        return self.ranking_statistic


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
            name=clean_str(co['company']),
            symbol=clean_str(co['symbol']),
            hq=clean_str(co['headquarters']),
            industry=clean_str(co['industry']),
            sector=clean_str(co['sector']),
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
    try:
        c1 = unpickle_company(ticker1)
    except IOError:
        c1 = ticker1

    try:
        c2 = unpickle_company(ticker2)
    except IOError:
        c2 = ticker2

    pa = PairAnalysis(c1, c2)
    pa.persist()
    return


def make_all_pairs(use_celery=False, skip_update=False, skip_pickle=False):
    """
    This will check all of the pairs, either threaded
    or via celery (i.e. local v cloud)
    """
    logger.info(colored('Collecting companies', 'white', attrs=['bold']))
    companies = Company.objects.all()
    tpool = ThreadPool(50)

    if not skip_update:
        logger.info(colored('Updating prices', 'white', attrs=['bold']))
        for c in companies:
            tpool.add_task(c.update_prices)
        tpool.wait_completion()
        logger.info(colored('Prices updated', 'white', attrs=['bold']))

    symbols = [c.symbol for c in companies]

    if not skip_pickle:
        logger.info(colored('Pickling companies', 'white', attrs=['bold']))
        pickle_all_companies()

    logger.info(colored('Updating workers', 'white', attrs=['bold']))
    update_workers()

    if use_celery:
        for s1, s2 in itertools.combinations(symbols, 2):
            make_pair.delay(s1, s2)

    else:

        for s1, s2 in itertools.combinations(symbols, 2):
            tpool.add_task(make_pair, s1, s2)
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
        c.writerow(['symbol', 'symbol_1', 'symbol_2', 'ranking_stat', 'avg_adf', 'avg_freq',
                    'industry_1', 'industry_2', 'sector_1', 'sector_2'])
	sorted_pairs = sorted(pairs, key=lambda x: x.ranking_statistic)
        short_pairs = sorted_pairs[:int(len(pairs) * threshold / 100) - 1]
        for p in short_pairs:
            row_data = p.csv_data()
            c.writerow(row_data + [industries[row_data[1]], industries[row_data[2]],
                                   sectors[row_data[1]], sectors[row_data[2]]])

    return None


def pickle_company(symbol):
    filename = os.path.join(os.getcwd(), 'coint', 'data', symbol)
    with gzip.open(filename, 'wb') as f:
        company = Company.objects.get(symbol=symbol)
        company.get_prices()
        pickle.dump(company, f)

    return None


def unpickle_company(symbol):
    filename = os.path.join(os.getcwd(), 'coint', 'data', symbol)
    with gzip.open(filename, 'rb') as f:
        company = pickle.load(f)

    return company


def pickle_all_companies():
    tpool = ThreadPool(50)
    companies = Company.objects.all()
    for c in companies:
        tpool.add_task(pickle_company, c.symbol)
    tpool.wait_completion()

    return None


def update_workers():
    subprocess.call(['git', 'commit', '-m', 'automated data update commit'])
    subprocess.call(['drone', '--ps:update'])

    return None
