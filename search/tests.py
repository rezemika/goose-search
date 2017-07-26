from django.test import TestCase
from django.core.exceptions import ValidationError
from search.models import SearchPreset

class SearchPresetTest(TestCase):
    """
        Test the validation of processing rules.
    """
    
    def test_validation(self):
        # Create a SearchPreset.
        # The osm_keys validation should work.
        sp = SearchPreset()
        sp.name = "Boulangerie"
        sp.slug_name="boulangerie"
        sp.osm_keys='"shop"="bakery"'
        try:
            sp.full_clean()
        except ValidationError:
            self.fail('Une exception "ValidationError" a été levée'
            ' pour le test des "osm_keys" monolignes.')
        # Test the validation of multiline osm_keys.
        sp.osm_keys += '\n"shop"="pastry"'
        try:
            sp.full_clean()
        except ValidationError:
            self.fail('Une exception "ValidationError" a été levée'
            ' pour le test des "osm_keys" multilignes.')
        # Test the processing_rules validation.
        sp.processing_rules = 'DISPLAY "Nom":"name"'
        sp.full_clean()
        
        sp.processing_rules = '"fee" "Payant":["yes":"Oui"|"no":"Non"]'
        sp.full_clean()
        
        sp.processing_rules = ('"surface" "Revêtement":'
            '["asphalt":"Bitume"|"dirt":"Terre"|'
            '"paving_stones":"Pavage de pierres"]')
        sp.full_clean()
        
        sp.processing_rules = ('"surface" "Revêtement":'
            '["asphalt":"Bitume"|"dirt":"Terre"|'
            '"*":"Autre"]')
        sp.full_clean()
        
        sp.processing_rules = ('"surface" "Revêtement":'
            '["asphalt":"Bitume"|"dirt":"Terre"|'
            '"paving_stones":"Pavage de pierres"]\n'
            'DISPLAY "Nom":"name"')
        sp.full_clean()
        
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
        Test the search views.
    """
    # TODO
    def geo_search_test(self):
        return
    
    def geo_results_test(self):
        return
    
    def geo_get_results_test(self):
        return
