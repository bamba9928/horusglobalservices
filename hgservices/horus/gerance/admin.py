from django.contrib import admin
from django.http import HttpResponse
import openpyxl
from reportlab.pdfgen import canvas
from .models import Vehicule, Bureau, Apporteur


# Personnalisation de l'en-tête de l'administration
admin.site.site_header = "Horus Global Services"
admin.site.site_title = "Gestion Production"
admin.site.index_title = "Bienvenue dans l'Administration"


# Exportation en PDF
def exporter_en_pdf(modeladmin, request, queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{modeladmin.model._meta.verbose_name_plural}.pdf"'

    p = canvas.Canvas(response)
    y = 800  # Position verticale de départ

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, y, f"Liste des {modeladmin.model._meta.verbose_name_plural}")
    y -= 40

    for obj in queryset:
        p.setFont("Helvetica", 12)
        p.drawString(50, y, str(obj))  # Appelle __str__() pour afficher l'objet
        y -= 20

        if y < 50:
            p.showPage()
            y = 800

    p.save()
    return response


exporter_en_pdf.short_description = "Exporter en PDF"


# Exportation en Excel
def exporter_en_excel(modeladmin, request, queryset):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Export"

    columns = [field.verbose_name for field in modeladmin.model._meta.fields]
    ws.append(columns)

    for obj in queryset:
        row = [getattr(obj, field.name) for field in modeladmin.model._meta.fields]
        ws.append(row)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{modeladmin.model._meta.verbose_name_plural}.xlsx"'
    wb.save(response)
    return response


exporter_en_excel.short_description = "Exporter en Excel"


# Mixins pour restreindre l'accès aux objets créés par l'utilisateur
class CreatedByAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.save()


# Admin pour Apporteur
@admin.register(Apporteur)
class ApporteurAdmin(CreatedByAdminMixin, admin.ModelAdmin):
    list_display = (
        'nom_et_prenom',
        'bureau',
        'telephone',
        'mail',
        'versement',
        'note',
    )
    list_filter = ('bureau',)  # Filtrer par bureau
    search_fields = ('nom_et_prenom', 'telephone', 'mail')  # Barre de recherche
    ordering = ('nom_et_prenom', 'bureau')  # Tri par nom et bureau
    list_per_page = 20
    actions = [exporter_en_pdf, exporter_en_excel]


# Admin pour Bureau
@admin.register(Bureau)
class BureauAdmin(CreatedByAdminMixin, admin.ModelAdmin):
    list_display = (
        'numero_bureau',
        'nom_du_bureau',
        'gerant',
        'region',
        'departement',
        'localite',
        'telephone_bureau',
        'total_police_vendu',
        'versement',
    )
    list_filter = ('region', 'departement', 'localite')  # Filtrer par région et département
    search_fields = ('nom_du_bureau', 'numero_bureau', 'gerant')  # Barre de recherche
    ordering = ('region', 'nom_du_bureau')  # Ordre par région et nom
    list_per_page = 20
    actions = [exporter_en_pdf, exporter_en_excel]


# Admin pour Vehicule
@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = (
        'apporteur',
        'immatriculation',
        'marque_et_modele',
        'police',
        'formatted_date_effet',
        'formatted_date_echeances',
        'duree_en_mois',
        'souscripteur',
        'categorie',
        'puissance_fiscale',
        'nombre_de_place',
        'nom_du_client',
        'prenom_du_client',
        'telephone',
        'mail',
        'avance',
        'reste',
        'payer',
        'created_at',
        'updated_at',
    )
    list_filter = ('apporteur', 'date_effet', 'date_echeances')
    search_fields = (
        'apporteur',
        'immatriculation',
        'police',
        'souscripteur',
        'nom_du_client',
        'prenom_du_client',
        'telephone',
        'mail',
    )
    ordering = ('apporteur', 'date_effet', 'immatriculation')
    list_per_page = 20
    actions = [exporter_en_pdf, exporter_en_excel]

    def formatted_date_effet(self, obj):
        return obj.date_effet.strftime('%d/%m/%Y') if obj.date_effet else None
    formatted_date_effet.short_description = "Date Effet"

    def formatted_date_echeances(self, obj):
        return obj.date_echeances.strftime('%d/%m/%Y') if obj.date_echeances else None
    formatted_date_echeances.short_description = "Date Échéance"
