from django import forms
from .models import Vehicule

class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        fields = '__all__'
        widgets = {
            'date_effet': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_echeances': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'payer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'nom_du_client': 'Nom du Client',
            'prenom_du_client': 'Prénom du Client',
            'adresse': 'Adresse',
            'telephone': 'Téléphone',
            'mail': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super(VehiculeForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.Select)):
                field.widget.attrs['class'] = 'form-control'
