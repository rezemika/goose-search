from django import forms
from search.models import SearchPreset
import geopy
from goose import settings

geolocator = geopy.geocoders.Nominatim(timeout=2000)

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
    search_preset = forms.ModelChoiceField(label="Votre recherche",
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
        attempts = 0
        while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
            try:
                if user_address:
                    calculated_position = geolocator.geocode(
                        user_address, language="fr"
                    )
                else:
                    coords = (float(user_latitude), float(user_longitude))
                    calculated_position = geolocator.reverse(
                        coords, language="fr"
                    )
                break
            except geopy.exc.GeopyError as e:
                attempts += 1
                if attempts == settings.GOOSE_META["max_geolocation_attempts"]:
                    raise e
        if calculated_position is None:
            raise forms.ValidationError(
                "L'adresse renseignée n'a pas permis de vous "
                "localiser. Vous pouvez essayer de la "
                "préciser, par exemple avec un code postal."
            )
        else:
            calculated_address = calculated_position.address
            cleaned_data["user_latitude"] = calculated_position.latitude
            cleaned_data["user_longitude"] = calculated_position.longitude
        cleaned_data["calculated_address"] = calculated_address
        return cleaned_data
