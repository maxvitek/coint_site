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
    html = coint(request, symbol).content.decode(encoding='UTF-8')
    return json.dumps(dict(html=html))