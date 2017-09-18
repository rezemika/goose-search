# -*- coding: utf-8 -*-
#
#  Loads data in DB to allow rapid testing.
#  
#  Published under the AGPLv3 license by rezemika.
#  

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.contrib.auth.models import User
from search.models import SearchPreset

class Command(BaseCommand):
    help = "Loads data in DB to allow rapid testing"
    
    def handle(self, *args, **options):
        # Creates an admin.
        try:
            user = User.objects.create_user("admin", "admin@example.com", "password")
            user.save()
        except IntegrityError:
            self.stdout.write(self.style.ERROR(
                "Un utilisateur 'admin' est déjà présent en BDD. "
                "Génération des SearchPresets uniquement."
            ))
        # Creates two search presets.
        sp1 = SearchPreset(
            name="Boulangerie / Pâtisserie",
            osm_keys='"shop"="bakery"\n"shop"="pastry"',
            processing_rules='"shop" "Type":["bakery":"Boulangerie"|"pastry":"Pâtisserie"]'
        )
        sp1.save()
        sp2 = SearchPreset(
            name="Parking",
            osm_keys='"amenity"="parking"',
            processing_rules='"fee" "Payant":["yes":"Oui"|"no":"Non"]\n"access" "Accès":["yes":"Public"|"permissive":"Autorisé"|"private":"Privé"]'
        )
        sp2.save()
        sp3 = SearchPreset(
            name="Hôtel / Motel / Auberge",
            osm_keys='"tourism"="hotel"\n"building"="hotel"\n"tourism"="hostel"\n"tourism"="motel"',
            processing_rules='"tourism" "Type":["hotel":"Hôtel"|"hostel":"Auberge"|"motel":"Motel"]\nDISPLAY "Étoiles":"stars"'
        )
        sp3.save()
        sp4 = SearchPreset(
            name="Eau potable",
            osm_keys='"amenity"="drinking_water"\n"drinking_water"="yes"'
        )
        sp4.save()
        self.stdout.write(self.style.SUCCESS("Données de test correctement chargées !"))
        return

