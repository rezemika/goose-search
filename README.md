Goose — Un moteur de recherche géographique utilisant OpenStreetMap
===================================================================

**Goose** (acronyme récursif pour *Goose Offers an Openstreetmap Search Engine*) est un moteur de recherche géographique utilisant les données d’OpenStreetMap pour retourner une liste de points d’intérêt à proximité. Il est disponnible à l’adresse [goose-sear.ch](https://goose-sear.ch/).

# Fonctionnalités

- Bouton "Me localiser" évitant d’avoir à retranscrire ses coordonnées GPS.
- Possibilité de renseigner une adresse au lieu de ses coordonnées GPS.
- Chargement des résultats avec Ajax.
- Affichage des propriétés des résultat modifiable selon la recherche effectuée.
- Version ultralégère (Goose Light), proposant des pages épurées (environ 25Ko pour 15 résultats).
- Permaliens de recherche, permettant refaire une même recherche sans re-remplir le formulaire.
- Carte des résultats avec [Leaflet](http://leafletjs.com/).

# Installation

- Cloner le dépôt : `git clone https://github.com/rezemika/goose-search/`
- Se placer sur une version spécifique : `git checkout -b vX.X.X`
- Entrer dans un virtual environment en Python 3.
- Installer les dépendances : `make install-back`
- Faire les migrations : `make migrate`
- Collecter les fichiers statiques : `make collectstatic`
- Compiler les fichiers de traduction (`.po`) : `python3 manage.py compilemessages -l <LANG>`
- Générer une nouvelle SECRET_KEY : `make new-secret-key`
- Charger les "données d’usine" : `make load-factory-data`
- Lancer les tests unitaires : `make test`
- Lancer le serveur de développement : `make run-back`

# Licence

Le code source de Goose est publié sous la licence AGPLv3, dont les termes peuvent être trouvés dans le fichier [LICENCE](LICENCE).
