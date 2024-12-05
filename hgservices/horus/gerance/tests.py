from django.test import TestCase

# Create your tests here.
# models.py
from django.db import models

class Vehicule(models.Model):
    police = models.CharField(max_length=50)
    immatriculation = models.CharField(max_length=20)
    date_effet = models.DateField()
    date_echeance = models.DateField()
    apporteur = models.CharField(max_length=100)
