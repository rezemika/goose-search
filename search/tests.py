from django.test import TestCase
from django.core.exceptions import ValidationError
from search.models import SearchPreset
from search.forms import SearchForm
from django.contrib.auth.models import User
from django.utils.html import escape
from search.views import utils

class UtilsTest(TestCase):
    """
        Tests the 'utils' functions.
    """
    def test_deg2dir(self):
        self.assertEqual(utils.deg2dir(10), "N ↑")
        self.assertEqual(utils.deg2dir(350), "N ↑")
        self.assertEqual(utils.deg2dir(95), "E →")
        self.assertEqual(utils.deg2dir(365), "N ↑")
        return
    
    def test_get_bearing(self):
        self.assertEqual(
            utils.get_bearing((47.2044, -1.5474), (47.4694, -0.5596)),
            290.6
        )
        self.assertEqual(
            utils.get_bearing((48.8500, 2.3325), (51.5044, -0.1113)),
            244.4
        )
        return

class SearchPresetTest(TestCase):
    """
        Tests the validation of processing rules.
    """
    def test_validation_valid(self):
        sp = SearchPreset()
        sp.name = "Boulangerie"
        sp.slug_name="boulangerie"
        sp.osm_keys='"shop"="bakery"'
        sp.full_clean()
        # Tests the validation of multiline osm_keys.
        sp.osm_keys += '\n"shop"="pastry"'
        sp.full_clean()
        # Tests the processing_rules validation.
        sp.processing_rules = 'DISPLAY "Nom":"name"'
        sp.full_clean()
        sp.processing_rules = '"fee" "Payant":["yes":"Oui"|"no":"Non"]'
        sp.full_clean()
        sp.processing_rules = (
            '"surface" "Revêtement":'
            '["asphalt":"Bitume"|"dirt":"Terre"|'
            '"paving_stones":"Pavage de pierres"]'
        )
        sp.full_clean()
        sp.processing_rules = (
            '"surface" "Revêtement":'
            '["asphalt":"Bitume"|"dirt":"Terre"|'
            '"*":"Autre"]'
        )
        sp.full_clean()
        sp.processing_rules = (
            '"surface" "Revêtement":'
            '["asphalt":"Bitume"|"dirt":"Terre"|'
            '"paving_stones":"Pavage de pierres"]\n'
            'DISPLAY "Nom":"name"'
        )
        sp.full_clean()
        return
    
    def test_validation_invalid(self):
        sp = SearchPreset()
        sp.name = "Boulangerie"
        sp.slug_name="boulangerie"
        sp.osm_keys='"shop"="bakery"'
        sp.save()
        with self.assertRaises(ValidationError):
            sp.processing_rules = 'DISPLAY "Nom" "name"'
            sp.full_clean()
        with self.assertRaises(ValidationError):
            sp.processing_rules = 'DISPLAY "Nom":"name'
            sp.full_clean()
        with self.assertRaises(ValidationError):
            sp.processing_rules = 'DISPLAY Nom":"name"'
            sp.full_clean()
        with self.assertRaises(ValidationError):
            sp.processing_rules = 'DISPLA "Nom":"name"'
            sp.full_clean()
        with self.assertRaises(ValidationError):
            sp.processing_rules = '"fee "Payant":["yes":"Oui"|"no":"Non"]'
            sp.full_clean()
        with self.assertRaises(ValidationError):
            sp.processing_rules = '"fee" "Payant" ["yes":"Oui"|"no":"Non"]'
            sp.full_clean()
        with self.assertRaises(ValidationError):
            sp.processing_rules = '"fee" "Payant" ["yes" "Oui"|"no":"Non"]'
            sp.full_clean()
        with self.assertRaises(ValidationError):
            sp.processing_rules = '"fee" "Payant" ["yes":"Oui"|"no":"Non"'
            sp.full_clean()
        return

class ViewsTest(TestCase):
    """
        Tests the normal search views.
    """
    def setUp(self):
        search_preset = SearchPreset(
            name="Boulangerie / Pâtisserie",
            osm_keys='"shop"="bakery"\n"shop"="pastry"',
            processing_rules='"fee" "Payant":["yes":"Oui"|"no":"Non"]'
        )
        search_preset.save()
        self.search_preset_id = search_preset.id
        return
    
    def test_js_variables(self):
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        if not form.is_valid():
            self.fail("Validation of the form failed.")
        form.clean()
        response = self.client.post('/', data=form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "var userLatitude = 64.14624;")
        self.assertContains(response, "var userLongitude = -21.94259;")
        self.assertContains(response, "var radius = 500;")
        self.assertContains(response, "var searchPresetId = {};".format(
            self.search_preset_id)
        )
        print(response.content)
        self.assertContains(response, "var noPrivate = true;")
        return
    
    def test_results_page(self):
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        if not form.is_valid():
            self.fail("La validation du formulaire a échoué.")
        form.clean()
        response = self.client.post('/', data=form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Voici votre localisation ")
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, "Adresse : ")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 500 mètres.")
        self.assertContains(response, "Exclusion des résultats à accès privé.")
        # Same test, but including private results.
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "False"
        }
        form = SearchForm(form_data)
        if not form.is_valid():
            self.fail("La validation du formulaire a échoué.")
        form.clean()
        response = self.client.post('/', data=form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Voici votre localisation ")
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, "Adresse : ")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 500 mètres.")
        self.assertContains(response, "Inclusion des résultats à accès privé.")
        return
    
    def test_normal_search_ajax(self):
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset_id": self.search_preset_id,
            "no_private": "true"
        }
        # See http://ericholscher.com/blog/2009/apr/16/testing-ajax-views-django/
        response = self.client.post(
            '/getresults/', data=form_data, follow=True,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        json = response.json()
        # Checks metadata.
        if json["status"] != "ok":
            self.fail("The status is not 'ok' ({}).".format(json["status"]))
        if json["debug_msg"] != '':
            self.fail("The debug message is not '' ({}).".format(json["debug_msg"]))
        if json["err_msg"] != '':
            self.fail("The error message is not '' ({}).".format(json["err_msg"]))
        # Checks the test result.
        test_result = None
        for result in json["content"]:
            if "Nom : City Hall of Reykjavik" in result:
                test_result = result
        if not test_result:
            self.fail("Test result can not be found.")
        if "Distance : 11990937 mètres" not in test_result:
            self.fail("The distance from the test result can not be found.")
        if "Direction : 107.6° E →" not in test_result:
            self.fail("The direction from thee test result can not be found.")
        if (
            'Téléphone : <a href="tel:+354 411 1111">'
            '+354 411 1111</a>'
        ) not in test_result:
            self.fail("The phone number of the test result can not be found.")
        if (
                'Téléphone : <a href="tel:+354 411 1111">+354 411 1111</a>'
                '\n\nAdresse estimée : '
            ) not in test_result:
            self.fail("The address of the test result can not be found.")
        return

class LightViewsTest(TestCase):
    """
        Tests the light search views.
    """
    def setUp(self):
        search_preset = SearchPreset(
            name="Boulangerie / Pâtisserie",
            osm_keys='"shop"="bakery"\n"shop"="pastry"',
            processing_rules='"fee" "Payant":["yes":"Oui"|"no":"Non"]'
        )
        search_preset.save()
        self.search_preset_id = search_preset.id
        return
    
    def test_light_search(self):
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        if not form.is_valid():
            self.fail("Validation of the form failed.")
        form.clean()
        response = self.client.post('/light/', data=form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base_light.html")
        self.assertContains(response, "Voici votre localisation ")
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, "Adresse : ")
        self.assertContains(
            response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;'
        )
        self.assertContains(response, " dans un rayon de 500 mètres.")
        self.assertContains(response, "Exclusion des résultats à accès privé.")
        self.assertContains(response, "Nom : City Hall of Reykjavik")
        self.assertContains(response, "Distance : 11990937 mètres")
        self.assertContains(response, "Direction : 107.6° E →")
        self.assertContains(
            response, (
                'Téléphone : <a href="tel:+354 411 1111">'
                '+354 411 1111</a>'
            )
        )
        self.assertContains(
            response, (
                'Téléphone : <a href="tel:+354 411 1111">'
                '+354 411 1111</a><br/><br/>'
                'Adresse estimée : '
            )
        )
        # Same test, but including private results.
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "False"
        }
        form = SearchForm(form_data)
        if not form.is_valid():
            self.fail("Validation of the form failed.")
        form.clean()
        response = self.client.post('/light/', data=form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base_light.html")
        self.assertContains(response, "Inclusion des résultats à accès privé.")
        return

class OtherViewsTest(TestCase):
    """
        Tests the non-search views.
    """
    def test_normal_about_page(self):
        response = self.client.get('/about/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        return
    
    def test_light_about_page(self):
        response = self.client.get('/light/about/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base_light.html")
        return

class SearchFormTest(TestCase):
    """
        Tests the validation of the search form.
    """
    def setUp(self):
        search_preset = SearchPreset(
            name="Boulangerie / Pâtisserie",
            osm_keys='"shop"="bakery"\n"shop"="pastry"',
            processing_rules='"fee" "Payant":["yes":"Oui"|"no":"Non"]'
        )
        search_preset.save()
        self.search_preset_id = search_preset.id
        self.user = User.objects.create_superuser(
            "admin", "test@example.com", "admin"
        )
        return
    
    def test_form_validation_valid(self):
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        self.assertTrue(form.is_valid())
        form_data = {
            "user_latitude": "",
            "user_longitude": "",
            "user_address": "Fridtjof Nansens plass, Oslo",
            "radius": "800",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        self.assertTrue(form.is_valid())
        return
    
    def test_form_validation_invalid(self):
        # Address and coordinates.
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "Fridtjof Nansens plass, Oslo",
            "radius": "800",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        self.assertFalse(form.is_valid())
        # Neither address nor coordinates.
        form_data = {
            "user_latitude": "",
            "user_longitude": "",
            "user_address": "",
            "radius": "800",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        # No radius.
        form_data = {
            "user_latitude": "",
            "user_longitude": "",
            "user_address": "Fridtjof Nansens plass, Oslo",
            "radius": "",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        self.assertFalse(form.is_valid())
        # Invalid search preset.
        form_data = {
            "user_latitude": "",
            "user_longitude": "",
            "user_address": "Fridtjof Nansens plass, Oslo",
            "radius": "500",
            "search_preset": "9999",
            "no_private": "on"
        }
        form = SearchForm(form_data)
        self.assertFalse(form.is_valid())
        # Invalid address.
        form_data = {
            "user_latitude": "",
            "user_longitude": "",
            "user_address": "Fridof Nansens plass, Oslo",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        form.is_valid()
        with self.assertRaises(ValidationError):
            form.clean(mocking_parameters="invalid_address")
        return
    
    def test_session_data(self):
        form_data = {
            "user_latitude": "64.14624",
            "user_longitude": "-21.94259",
            "user_address": "",
            "radius": "500",
            "search_preset": self.search_preset_id,
            "no_private": "on"
        }
        form = SearchForm(form_data)
        if not form.is_valid():
            self.fail("Validation of the form failed.")
        form.clean()
        response = self.client.post('/', form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertEqual(type(session["search_form"]["user_latitude"]), float)
        self.assertEqual(type(session["search_form"]["user_longitude"]), float)
        self.assertEqual(type(session["search_form"]["user_address"]), str)
        self.assertEqual(session["search_form"]["radius"], 500)
        self.assertEqual(session["search_form"]["search_preset_id"], self.search_preset_id)
        self.assertEqual(session["search_form"]["no_private"], True)
        return

class PermalinkTest(TestCase):
    """
        Tests the functioning of permalinks.
    """
    def setUp(self):
        search_preset = SearchPreset(
            name="Boulangerie / Pâtisserie",
            osm_keys='"shop"="bakery"\n"shop"="pastry"',
            processing_rules='"fee" "Payant":["yes":"Oui"|"no":"Non"]'
        )
        search_preset.save()
        self.search_preset_id = search_preset.id
        return
    
    def escape_request_uri(self, response):
        return bytes(escape(response.wsgi_request.build_absolute_uri()), encoding='utf-8')
    
    def test_normal_valid_permalinks(self):
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<center><em>")
        self.assertContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(
            response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;'
        )
        self.assertContains(response, " dans un rayon de 500 mètres.")
        self.assertContains(response, "Exclusion des résultats à accès privé.")
        
        # Same test, but including private results.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500",
            "no_private": "0"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<center><em>")
        self.assertContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(
            response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;'
        )
        self.assertContains(response, " dans un rayon de 500 mètres.")
        self.assertContains(response, "Inclusion des résultats à accès privé.")
        return
    
    def test_normal_invalid_permalinks(self):
        # Invalid search preset.
        get_data = {
            "sp": "9999",
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>L&#39;ID de l&#39;objet de votre recherche est invalide.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, 'Recherche : Paramètres invalides.')
        # Invalid radius.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "azerty",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>Le rayon de recherche demandé est invalide.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 0 mètres.")
        # Invalid radius (again).
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "5",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>Le rayon de recherche demandé est invalide.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 0 mètres.")
        # Invalid coordinates.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "azerty",
            "lon": "qwerty",
            "radius": "500",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>Vos coordonnées sont invalides.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 0.0")
        self.assertContains(response, "Longitude : 0.0")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 500 mètres.")
        # Missing parameter.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500"
        }
        response = self.client.get('/results/', get_data)
        self.assertRedirects(response, '/')
        return
    
    def test_light_valid_permalinks(self):
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500",
            "no_private": "1"
        }
        response = self.client.get('/light/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<center><em>")
        self.assertContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(
            response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;'
        )
        self.assertContains(response, " dans un rayon de 500 mètres.")
        self.assertContains(response, "Exclusion des résultats à accès privé.")
        self.assertContains(response, "Nom : City Hall of Reykjavik")
        
        # Same test, but including private results.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500",
            "no_private": "0"
        }
        response = self.client.get('/light/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<center><em>")
        self.assertContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(
            response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;'
        )
        self.assertContains(response, " dans un rayon de 500 mètres.")
        self.assertContains(response, "Inclusion des résultats à accès privé.")
        self.assertContains(response, "Nom : City Hall of Reykjavik")
        return
    
    def test_light_invalid_permalinks(self):
        # Invalid search preset.
        get_data = {
            "sp": "9999",
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>L&#39;ID de l&#39;objet de votre recherche est invalide.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, 'Recherche : Paramètres invalides.')
        # Invalid radius.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "azerty",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>Le rayon de recherche demandé est invalide.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 0 mètres.")
        # Invalid radius (again).
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "5",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>Le rayon de recherche demandé est invalide.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 64.14624")
        self.assertContains(response, "Longitude : -21.94259")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 0 mètres.")
        # Invalid coordinates.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "azerty",
            "lon": "qwerty",
            "radius": "500",
            "no_private": "1"
        }
        response = self.client.get('/results/', get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<center><em>Vos coordonnées sont invalides.</em></center>")
        self.assertNotContains(response, self.escape_request_uri(response))
        self.assertContains(response, "Latitude : 0.0")
        self.assertContains(response, "Longitude : 0.0")
        self.assertContains(response, 'Recherche : &quot;Boulangerie / Pâtisserie&quot;')
        self.assertContains(response, " dans un rayon de 500 mètres.")
        # Missing parameter.
        get_data = {
            "sp": self.search_preset_id,
            "lat": "64.14624",
            "lon": "-21.94259",
            "radius": "500"
        }
        response = self.client.get('/light/', get_data)
        self.assertNotContains(response, "Résultats de la recherche")
        return
