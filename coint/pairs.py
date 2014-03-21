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

logger = logging.getLogger(__name__)


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
    return [ticker1, ticker2], result[0], result[4]


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

