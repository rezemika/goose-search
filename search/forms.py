from django import forms
from search.models import SearchPreset

class SearchForm(forms.Form):
    """
        The form used on the main page to search a point of interest.
    """
    user_latitude = forms.DecimalField(label="Latitude",
        min_value=-90, max_value=90, required=False,
        widget=forms.TextInput(attrs=
        {"id": "user_latitude", "type":"number", "step": "any",
        "class": "form-control"}))
    user_longitude = forms.DecimalField(label="Longitude",
        min_value=-90, max_value=90, required=False,
        widget=forms.TextInput(attrs=
        {"id": "user_longitude", "type":"number", "step": "any",
        "class": "form-control"}))
    user_address = forms.CharField(label="Adresse estimée",
        required=False, widget=forms.TextInput(attrs=
            {"class": "form-control",
            "placeholder": "entrer une adresse manuellement"}))
    radius = forms.IntegerField(label="Rayon de recherche",
        help_text="en mètres",
        min_value=100, max_value=2000, initial=500,
        widget=forms.NumberInput(attrs=
            {"class": "form-control", "step": 50}))
    searched_target = forms.ModelChoiceField(label="Votre recherche",
        queryset=SearchPreset.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}))
    no_private = forms.BooleanField(required=False, initial=True,
        label="Écarter les résultats à accès privé ?")
    
    def clean(self):
        """
            Check that GPS coords or address are given.
        """
        cleaned_data = super(SearchForm, self).clean()
        user_latitude = cleaned_data.get("user_latitude")
        user_longitude = cleaned_data.get("user_longitude")
        user_address = cleaned_data.get("user_address")
        if not user_latitude or not user_longitude:
            if not user_address:
                raise forms.ValidationError("Vous devez renseigner"
                    " vos coordonnées GPS ou votre adresse actuelle.",
                    code='invalid')
