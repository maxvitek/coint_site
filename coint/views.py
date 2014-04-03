from django.shortcuts import render
from django.utils.timezone import activate
import logging
from coint.pairs import PairAnalysis

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
    if 'detected_tz' in request.session.keys():
        tz = request.session['detected_tz']
        activate(tz)
    symbol_1, symbol_2 = symbol.split('-')
    logger.warning('coint view: ' + request.META.get('REMOTE_ADDR'))

    pa = PairAnalysis(symbol_1, symbol_2, lookback=1)

    return render(request, template_name='coint.html', dictionary={'pair_analysis': pa})

