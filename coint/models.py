from django.db import models


class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    symbol = models.CharField(max_length=20)
    hq = models.CharField(max_length=150)
    industry = models.CharField(max_length=150)
    sector = models.CharField(max_length=150)
    tempodb = models.IntegerField()