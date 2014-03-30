from django.shortcuts import render
from django.utils.timezone import activate
from coint_site.settings import TIME_ZONE
import logging
from coint.pairs import get_pair

activate(TIME_ZONE)

logger = logging.getLogger(__name__)


def home(request):
    """
    Sends the visitor to the homepage

    :param request: http request object
    :return:
    """
    logger.warning('home view: ' + request.META.get('REMOTE_ADDR'))

    pair_data = get_pair('AAPL', 'GOOG')
    logger.info('Got pair data.')
    return render(request, template_name='home.html', dictionary={
        'data': pair_data, 'ticker1': 'AAPL', 'ticker2': 'GOOG'})


def coint(request, symbol):
    """
    Sends the visitor some coint html + js

    :param request: http request object
    :return:
    """
    symbol_1, symbol_2 = symbol.split('-')
    logger.warning('coint view: ' + request.META.get('REMOTE_ADDR'))

    pair_data = get_pair(symbol_1, symbol_2)
    logger.info('Got pair data.')
    return render(request, template_name='coint.html', dictionary={
        'data': pair_data, 'ticker1': symbol_1, 'ticker2': symbol_2})
