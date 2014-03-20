from __future__ import absolute_import
from celery import Celery

from coint_site.settings import BROKER_URL

app = Celery('coint',
             broker=BROKER_URL,
             backend=BROKER_URL,
             include=[])

app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=300,  # short expiration
    CELERY_ACKS_LATE=True  # rerunning tasks is ok
)