from django import forms
from search.models import SearchPreset
import geopy
from goose import settings
from search import utils

class SearchForm(forms.Form):
    """
        The form used on the main page to search a point of interest.
    """
    user_latitude = forms.DecimalField(
        label="Latitude",
        min_value=-90, max_value=90, required=False,
        widget=forms.TextInput(attrs={
            "id": "user_latitude", "type":"number", "step": "any",
            "class": "form-control"
        })
    )
    user_longitude = forms.DecimalField(
        label="Longitude",
        min_value=-90, max_value=90, required=False,
        widget=forms.TextInput(attrs={
            "id": "user_longitude", "type":"number", "step": "any",
            "class": "form-control"
        })
    )
    user_address = forms.CharField(
        label="Adresse estimée",
        required=False, widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "entrer une adresse manuellement"
        })
    )
    radius = forms.IntegerField(
        label="Rayon de recherche",
        help_text="en mètres",
        min_value=settings.GOOSE_META["radius_extreme_values"][0],
        max_value=settings.GOOSE_META["radius_extreme_values"][1],
        initial=500,
        widget=forms.NumberInput(attrs={
            "class": "form-control", "step": 50
        })
    )
    search_preset = forms.ModelChoiceField(
        label="Votre recherche",
        queryset=SearchPreset.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"})
    )
    no_private = forms.BooleanField(
        required=False, initial=True,
        label="Écarter les résultats à accès privé ?")
    
    def clean(self, mocking_parameters=None):
        """
            Check that GPS coords or address are given.
        """
        cleaned_data = super(SearchForm, self).clean()
        user_latitude = cleaned_data.get("user_latitude")
        user_longitude = cleaned_data.get("user_longitude")
        user_address = cleaned_data.get("user_address")
        if not user_latitude or not user_longitude:
            if not user_address:
                raise forms.ValidationError(
                    "Vous devez renseigner vos coordonnées GPS ou "
                    "votre adresse actuelle.",
                    code='invalid'
                )
        if all((user_latitude, user_longitude, user_address)):
            raise forms.ValidationError(
                "Vous devez renseigner soit vos coordonnées GPS, soit "
                "votre adresse actuelle (mais pas les deux).",
                code='invalid'
            )
        elif not user_address and not all([user_latitude, user_longitude]):
            raise forms.ValidationError(
                "Il manque la latitude ou la longitude dans les "
                "coordonnées GPS fournies. Vous pouvez alternativement "
                "fournir une adresse.",
                code='invalid'
            )
        position = None  # TODO : Remove?
        if user_address:
            position = utils.get_address(
                address=user_address,
                mocking_parameters=mocking_parameters
            )
        else:
            position = utils.get_address(
                coords=(float(user_latitude), float(user_longitude)),
                mocking_parameters=mocking_parameters
            )
        if position is None:
            raise forms.ValidationError(
                "Les données renseignées n'ont pas permis de vous "
                "localiser. Vous pouvez essayer de la "
                "préciser, par exemple avec un code postal."
            )
        else:
            cleaned_data["latitude"] = position[0][0]
            cleaned_data["longitude"] = position[0][1]
            cleaned_data["calculated_address"] = position[1]
        return cleaned_data
