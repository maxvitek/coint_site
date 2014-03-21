from django.db import models
from coint_site.settings import TEMPODB
from tempodb import Client as TempoDBClient

tdb = TempoDBClient(
    TEMPODB['KEY'],
    TEMPODB['SECRET'],
    host=TEMPODB['HOST'],
    port=TEMPODB['PORT'],
    secure=TEMPODB['SECURE'],
)


class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    symbol = models.CharField(max_length=20)
    hq = models.CharField(max_length=150)
    industry = models.CharField(max_length=150)
    sector = models.CharField(max_length=150)
 #   ts = tdb.read_key(symbol)