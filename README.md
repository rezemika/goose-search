Goose - Un moteur de recherche géographique utilisant OpenStreetMap
===================================================================

**Goose** (acronyme récursif pour *Goose Offers an Openstreetmap Search Engine*) est un moteur de recherche géographique utilisant les données d'OpenStreetMap pour retourner une liste de points d'intérêt à proximité. Il est disponnible à l'adresse [goose-sear.ch](https://goose-sear.ch/).

**Version de production actuelle : 0.1.1**

This repository uses [the cactus model](https://barro.github.io/2016/02/a-succesful-git-branching-model-considered-harmful/). The development happens in the 'master' branch, the production versions are merged to the 'prod' branch.

# Fonctionnalités

- Bouton "Me localiser" évitant d'avoir à retranscrire ses coordonnées GPS
- Possibilité de renseigner une adresse au lieu de ses coordonnées GPS
- Chargement des résultats avec Ajax
- Affichage des propriétés des résultat modifiable selon la recherche effectuée

# TODO

- Version statique ne requérant pas JavaScript
- Recherche avancée avec tags personnalisés
- Tests unitaires

# Licence

Le code source de Goose est publié sous la licence AGPLv3, dont les termes peuvent être trouvés dans le fichier [LICENCE](LICENCE).
