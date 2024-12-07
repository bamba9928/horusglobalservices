# ....Mouhamadou Bamba Dieng ... 2024  Horus Global Services ...
#..... +221 77 249 05 30 bigrip2016@gmail.com ....

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

# Choix des régions
REGIONS_CHOICES = [
    ('Dakar', 'Dakar'),
    ('Diourbel', 'Diourbel'),
    ('Fatick', 'Fatick'),
    ('Kaolack', 'Kaolack'),
    ('Kaffrine', 'Kaffrine'),
    ('Kédougou', 'Kédougou'),
    ('Kolda', 'Kolda'),
    ('Louga', 'Louga'),
    ('Matam', 'Matam'),
    ('Saint-Louis', 'Saint-Louis'),
    ('Sédhiou', 'Sédhiou'),
    ('Tambacounda', 'Tambacounda'),
    ('Thiès', 'Thiès'),
    ('Ziguinchor', 'Ziguinchor'),
]

# Catégories de véhicules
CATEGORY_CHOICES = [(f"Categorie{i}", f"Categorie{i}") for i in range(1, 8)]


class Bureau(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bureaux")
    numero_bureau = models.CharField(max_length=10, unique=True, verbose_name="Numéro Bureau", db_index=True)
    nom_du_bureau = models.CharField(max_length=100, unique=True, verbose_name="Nom du Bureau", db_index=True)
    gerant = models.CharField(max_length=100, blank=True, null=True, verbose_name="Gérant")
    region = models.CharField(max_length=20, choices=REGIONS_CHOICES, verbose_name="Région")
    departement = models.CharField(max_length=100, blank=True, null=True, verbose_name="Département")
    localite = models.CharField(max_length=100, blank=True, null=True, verbose_name="Localité")
    telephone_bureau = models.CharField(max_length=15, unique=True, verbose_name="Téléphone Bureau", db_index=True)
    email = models.EmailField(blank=True, null=True, unique=True, verbose_name="Email")
    total_police_vendu = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Total Police Vendu", blank=True)
    versement = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Versement")
    note = models.TextField(blank=True, null=True, verbose_name="Note")

    class Meta:
        verbose_name_plural = "Bureaux"

    def __str__(self):
        return f"{self.nom_du_bureau} - {self.region}"

    def get_absolute_url(self):
        return reverse("bureau_detail", kwargs={"pk": self.pk})


class Apporteur(models.Model):
    bureau = models.ForeignKey(Bureau, on_delete=models.CASCADE, related_name="apporteurs", verbose_name="Bureau")
    nom_et_prenom = models.CharField(max_length=100, verbose_name="Nom et Prénom", db_index=True)
    telephone = models.CharField(max_length=15, unique=True, verbose_name="Téléphone", db_index=True)
    mail = models.EmailField(blank=True, null=True, unique=True, verbose_name="Mail")
    versement = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Versement", blank=True)
    note = models.TextField(blank=True, null=True, verbose_name="Note")

    def __str__(self):
        return self.nom_et_prenom


class Vehicule(models.Model):
    apporteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='policies_created')
    souscripteur = models.CharField(max_length=100, blank=True, verbose_name="Souscripteur")
    immatriculation = models.CharField(max_length=100, blank=True, unique=True, verbose_name="Immatriculation", db_index=True)
    marque_et_modele = models.CharField(max_length=100, blank=True, verbose_name="Marque et Modèle")
    police = models.CharField(max_length=50, blank=True, verbose_name="Police", db_index=True)
    duree_en_mois = models.IntegerField(choices=[(i, i) for i in range(1, 13)], verbose_name="Durée en Mois")
    date_effet = models.DateField(verbose_name="Date Effet")
    date_echeances = models.DateField(verbose_name="Date Échéances")
    categorie = models.CharField(max_length=15, choices=CATEGORY_CHOICES, verbose_name="Catégorie")
    puissance_fiscale = models.IntegerField(default=0, verbose_name="Puissance Fiscale", blank=True)
    nombre_de_place = models.IntegerField(default=0, verbose_name="Nombre de Places", blank=True)
    nom_du_client = models.CharField(max_length=100, blank=True, verbose_name="Nom du Client", db_index=True)
    prenom_du_client = models.CharField(max_length=100, blank=True, verbose_name="Prénom du Client", db_index=True)
    adresse = models.CharField(max_length=100, blank=True, verbose_name="Adresse", db_index=True)
    telephone = models.CharField(max_length=15, blank=True, unique=True, verbose_name="Téléphone", db_index=True)
    mail = models.EmailField(max_length=100, blank=True, verbose_name="Email", db_index=True)
    avance = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Avance", blank=True)
    reste = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Reste", blank=True)
    payer = models.BooleanField(default=False, verbose_name="Payé")
    note = models.TextField(blank=True, verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nom_du_client", "prenom_du_client", "telephone"],
                name="unique_vehicle_client"
            )
        ]

    def __str__(self):
        return f"{self.immatriculation} - {self.souscripteur}"

    def clean(self):
        if self.date_echeances <= self.date_effet:
            raise ValidationError({"date_echeances": "La date d'échéance doit être postérieure à la date d'effet."})
