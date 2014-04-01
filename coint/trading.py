import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz

from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform


class Pairtrade(TradingAlgorithm):
    """

    """
    def __init__(self, ticker1, ticker2, slope, intercept=0):
        TradingAlgorithm.__init__(self)
        self.spreads = []
        self.invested = 0
        self.slope = slope
        self.intercept = intercept
        self.ticker1 = ticker1
        self.ticker2 = ticker2

    def compute_zscore(self, spread):
        """1. Compute the spread given slope and intercept.
           2. zscore the spread.
        """
        zscore = (spread - np.mean(spread)) / np.std(spread)
        return zscore

    def place_orders(self, data, zscore):
        """Buy spread if zscore is > 2, sell if zscore < .5.
        """
        if zscore >= 2.0 and not self.invested:
            self.order('PEP', int(100 / data['PEP'].price))
            self.order('KO', -int(100 / data['KO'].price))
            self.invested = True
        elif zscore <= -2.0 and not self.invested:
            self.order('PEP', -int(100 / data['PEP'].price))
            self.order('KO', int(100 / data['KO'].price))
            self.invested = True
        elif abs(zscore) < .5 and self.invested:
            self.sell_spread()
            self.invested = False