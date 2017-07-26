# -*- coding: utf-8 -*-
#
#  Generates a new secret key and updates 'settings.py'.
#  
#  Published under the AGPLv3 license by rezemika.
#  

from django.core.management.base import BaseCommand, CommandError
import random, string

class Command(BaseCommand):
    help = "Generates a new SECRET_KEY and updates the 'settings.py' file"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--key", action="store", dest="key", type=str,
            help="Use a custom key"
        )
        return
    
    def handle(self, *args, **options):
        if options["key"]:
            self.replace_key(options["key"])
            self.stdout.write(self.style.SUCCESS("Fichier 'settings.py' mis a jour avec succès !"))
        else:
            new_key = self.new_secret_key()
            self.replace_key(new_key)
            self.stdout.write(self.style.SUCCESS("Nouvelle clé générée et fichier 'settings.py' mis a jour avec succès !"))
        return
    
    def random_char(self):
        return random.choice(string.printable[:-6].replace("'", '').replace('"', ''))
    
    def new_secret_key(self):
        output = ''
        while len(output) != 50:
            output += self.random_char()
        return output
    
    def replace_key(self, key):
        with open("goose/settings.py", 'r') as f:
            old_file = f.read()
        new_file = ""
        for line in old_file.splitlines(keepends=True):
            if line.startswith("SECRET_KEY = "):
                line = "SECRET_KEY = '{}'\n".format(self.new_secret_key())
            new_file += line
        with open("goose/settings.py", 'w') as f:
            f.write(new_file)
        return
