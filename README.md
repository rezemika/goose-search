Goose - Un moteur de recherche géographique utilisant OpenStreetMap
===================================================================

**Goose** (acronyme récursif pour *Goose Offers an Openstreetmap Search Engine*) est un moteur de recherche géographique utilisant les données d'OpenStreetMap pour retourner une liste de points d'intérêt à proximité. Il est disponnible à l'adresse [goose-sear.ch](https://goose-sear.ch/).

Ce dépôt utilise [le "cactus model"](https://barro.github.io/2016/02/a-succesful-git-branching-model-considered-harmful/). Le développement se fait dans la branche 'master', les versions de production sont mergées dans la branche 'prod'.

# Fonctionnalités

- Bouton "Me localiser" évitant d'avoir à retranscrire ses coordonnées GPS
- Possibilité de renseigner une adresse au lieu de ses coordonnées GPS
- Chargement des résultats avec Ajax
- Affichage des propriétés des résultat modifiable selon la recherche effectuée
- Version ultralégère (Goose Light), proposant des pages épurées (environ 25Ko pour 15 résultats)
- Permaliens de recherche, permettant refaire une même recherche sans re-remplir le formulaire

# Licence

Le code source de Goose est publié sous la licence AGPLv3, dont les termes peuvent être trouvés dans le fichier [LICENCE](LICENCE).
