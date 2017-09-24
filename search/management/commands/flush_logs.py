# -*- coding: utf-8 -*-
#
#  Generates a new secret key and updates 'settings.py'.
#  
#  Published under the AGPLv3 license by rezemika.
#  

from django.core.management.base import BaseCommand
import glob

class Command(BaseCommand):
    help = "Flushes all log files"
    
    def handle(self, *args, **options):
        for f in glob.glob("logs/*.log"):
            with open(f, 'w'):
                pass
        self.stdout.write(self.style.SUCCESS("Fichiers de logs effacés."))
