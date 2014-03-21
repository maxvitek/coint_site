from django.shortcuts import render
from pairs import get_pair
from django.utils.timezone import activate
from coint_site.settings import TIME_ZONE
import logging

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
    return render(request, template_name='home.html', dictionary={
        'data': pair_data, 'ticker1': 'AAPL', 'ticker2': 'GOOG'})
