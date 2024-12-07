# ....Mouhamadou Bamba Dieng ... 2024  Horus Global Services ...
#..... +221 77 249 05 30 bigrip2016@gmail.com ....


from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q
from django.contrib import messages
from reportlab.pdfgen import canvas
import csv
from django.http import HttpResponse
from .forms import VehiculeForm
from .models import Vehicule
from .messages import (
    VEHICLE_CREATED_SUCCESS,
    VEHICLE_UPDATED_SUCCESS,
    VEHICLE_DELETED_SUCCESS,
    NO_RESULTS_FOUND,
    ENTER_SEARCH_TERM,
)
from django.conf.urls import handler404

# Exportation des véhicules en CSV
@login_required
def export_vehicles_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vehicles.csv"'

    writer = csv.writer(response)
    writer.writerow(['Immatriculation', 'Marque et Modèle', 'Date Effet', 'Date Échéances'])

    # Filtrer les véhicules par utilisateur connecté
    vehicles = Vehicule.objects.filter(apporteur=request.user).values_list(
        'immatriculation', 'marque_et_modele', 'date_effet', 'date_echeances'
    )
    for vehicle in vehicles:
        writer.writerow(vehicle)

    return response


# Liste des véhicules
@login_required
def vehicule_list(request):
    vehicules = Vehicule.objects.filter(apporteur=request.user)

    # Récupérer les paramètres de filtrage depuis la requête GET
    date_echeance = request.GET.get('date_echeances')
    apporteur = request.GET.get('apporteur')

    # Appliquer les filtres si les paramètres sont fournis
    if date_echeance:
        vehicules = vehicules.filter(date_echeances=date_echeance)
    if apporteur:
        vehicules = vehicules.filter(apporteur__username__icontains=apporteur)

    # Passer les véhicules filtrés au template
    context = {
        'vehicules': vehicules,
    }
    return render(request, 'vehicule_list.html', context)


# Page d'accueil
def home(request):
    return render(request, 'home.html')


# Gestion des véhicules
@login_required
def gestion(request):
    return render(request, 'gestion.html')


# Recherche de véhicules
@login_required
def search(request):
    query = request.GET.get('q', '').strip()  # Récupération et suppression des espaces inutiles
    vehicules = Vehicule.objects.none()  # Initialisation par défaut

    if query:
        # Filtrage basé sur plusieurs champs avec Q (recherche insensible à la casse)
        vehicules = Vehicule.objects.filter(
            Q(immatriculation__icontains=query) |
            Q(police__icontains=query) |
            Q(souscripteur__icontains=query) |
            Q(nom_du_client__icontains=query) |
            Q(prenom_du_client__icontains=query) |
            Q(telephone__icontains=query) |
            Q(marque_et_modele__icontains=query)
        ).filter(apporteur=request.user)  # Filtrer par utilisateur connecté

        # Ajout d'un message d'avertissement si aucun résultat
        if not vehicules.exists():
            messages.warning(request, NO_RESULTS_FOUND.format(query))
    else:
        # Message informatif si aucune requête n'est entrée
        messages.info(request, ENTER_SEARCH_TERM)

    return render(request, 'search.html', {'vehicules': vehicules, 'query': query})


# Vue CBV : Liste des véhicules
class VehiculeListView(LoginRequiredMixin, ListView):
    model = Vehicule
    template_name = 'vehicule_list.html'
    context_object_name = 'vehicules'
    paginate_by = 20  # Pagination : 20 véhicules par page

    def get_queryset(self):
        # Filtrer les véhicules par utilisateur connecté
        return Vehicule.objects.filter(apporteur=self.request.user)


# Vue CBV : Détails d'un véhicule
class VehiculeDetailView(LoginRequiredMixin, DetailView):
    model = Vehicule
    template_name = 'vehicule_detail.html'
    context_object_name = 'vehicule'


# Vue CBV : Création d'un véhicule
class VehiculeCreateView(LoginRequiredMixin, CreateView):
    model = Vehicule
    form_class = VehiculeForm
    template_name = 'vehicule_form.html'
    success_url = reverse_lazy('vehicule_list')

    def form_valid(self, form):
        # Associer l'utilisateur connecté comme créateur
        form.instance.apporteur = self.request.user
        messages.success(self.request, VEHICLE_CREATED_SUCCESS)
        return super().form_valid(form)


# Vue CBV : Mise à jour d'un véhicule
class VehiculeUpdateView(LoginRequiredMixin, UpdateView):
    model = Vehicule
    form_class = VehiculeForm
    template_name = 'vehicule_form.html'
    success_url = reverse_lazy('vehicule_list')

    def form_valid(self, form):
        messages.success(self.request, VEHICLE_UPDATED_SUCCESS)
        return super().form_valid(form)


# Vue CBV : Suppression d'un véhicule
class VehiculeDeleteView(LoginRequiredMixin, DeleteView):
    model = Vehicule
    template_name = 'vehicule_confirm_delete.html'
    success_url = reverse_lazy('vehicule_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, VEHICLE_DELETED_SUCCESS)
        return super().delete(request, *args, **kwargs)






# Export

def export_vehicules_csv(request):
    # Récupérer les critères de recherche
    immatriculation = request.GET.get('immatriculation', '')
    nom_client = request.GET.get('nom_client', '')

    # Filtrer les résultats comme dans la vue de recherche
    vehicules = Vehicule.objects.all()
    if immatriculation:
        vehicules = vehicules.filter(immatriculation__icontains=immatriculation)
    if nom_client:
        vehicules = vehicules.filter(nom_du_client__icontains=nom_client)

    # Générer le fichier CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vehicules.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Immatriculation', 'Souscripteur', 'Marque et Modèle', 'Durée en Mois',
        'Date Effet', 'Date Échéance', 'Payé', 'Nom Client', 'Prénom Client'
    ])
    for vehicule in vehicules:
        writer.writerow([
            vehicule.immatriculation, vehicule.souscripteur, vehicule.marque_et_modele,
            vehicule.duree_en_mois, vehicule.date_effet, vehicule.date_echeances,
            "Oui" if vehicule.payer else "Non", vehicule.nom_du_client, vehicule.prenom_du_client
        ])
    return response

# EN PDF
def export_vehicules_pdf(request):
    # Récupérer les critères de recherche
    immatriculation = request.GET.get('immatriculation', '')
    nom_client = request.GET.get('nom_client', '')

    # Filtrer les résultats comme dans la vue de recherche
    vehicules = Vehicule.objects.all()
    if immatriculation:
        vehicules = vehicules.filter(immatriculation__icontains=immatriculation)
    if nom_client:
        vehicules = vehicules.filter(nom_du_client__icontains=nom_client)

    # Générer le fichier PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="vehicules.pdf"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Liste des Véhicules (Résultats filtrés)")
    y = 780
    for vehicule in vehicules:
        p.setFont("Helvetica", 12)
        p.drawString(50, y, f"{vehicule.immatriculation} - {vehicule.souscripteur} - {vehicule.marque_et_modele}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 800

    p.save()
    return response


def custom_page_not_found_view(request, exception):
    return render(request, '404.html', status=404)
