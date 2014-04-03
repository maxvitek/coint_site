from django.shortcuts import render
from django.utils.timezone import activate
from coint_site.settings import TIME_ZONE
import logging
from coint.pairs import PairAnalysis

activate(TIME_ZONE)

logger = logging.getLogger(__name__)


def home(request):
    """
    Sends the visitor to the homepage

    :param request: http request object
    :return:
    """
    logger.warning('home view: ' + request.META.get('REMOTE_ADDR'))
    return render(request, template_name='home.html')


def coint(request, symbol):
    """
    Sends the visitor some coint html + js

    :param request: http request object
    :return:
    """
    symbol_1, symbol_2 = symbol.split('-')
    logger.warning('coint view: ' + request.META.get('REMOTE_ADDR'))

    pa = PairAnalysis(symbol_1, symbol_2, lookback=1)

    return render(request, template_name='coint.html', dictionary={'pair_analysis': pa})

