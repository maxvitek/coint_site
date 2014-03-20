from intraday import get_google_data
import pandas as pd
from util import timestamp
import logging

logger = logging.getLogger(__name__)


def get_pair(ticker1, ticker2, data_frame_result=False):
    """
    We take two tickers and return either
    a pandas dataframe or a list of dicts
    depending on 'data_frame_result' kwarg
    :params ticker1: str
    :params ticker2: str
    :return DataFrame, list (of dicts)
    """
    df1 = get_google_data(ticker1)
    df2 = get_google_data(ticker2)
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