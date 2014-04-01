from dajaxice.decorators import dajaxice_register
import json
from coint.views import coint

@dajaxice_register
def ajax_coint(request, symbol=None):
    """
    Form the ajax request response
    """
    if not symbol:
        raise ValueError()

    #TODO crazy nested try block until I can figure out why these calls are failing when the data is not up to date
    try:
        html = coint(request, symbol).content.decode(encoding='UTF-8')
    except:
        try:
            html = coint(request, symbol).content.decode(encoding='UTF-8')
        except:
            html = coint(request, symbol).content.decode(encoding='UTF-8')
    return json.dumps(dict(html=html))