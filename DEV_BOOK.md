# DEV BOOK

Ce document explique la progression dans le développement du projet. Quand une étape est franchie, elle est marquée comme [OK]

Description du projet : ClapTrap est un service capable de reconnaitre, grâce à l'IA, des sons en provenance de différentes sources. Ces sources sont : microphone, RTSP, VBAN. A chaque source peut-être rattaché un webhook (une url). Si la source n'a pas de webhook attaché, aucun webhook n'est appelé.

# Etapes

Listing des sources audio micro [OK]
Listing des sources audio VBAN [OK]
Listing des sources RTSP via un fichier de configuration settings.json [OK]
Détection des claps à partir du son capté par le micro [OK]
Détection des claps à partir du son capté par la source RTSP [OK]
Détection des claps à partir du son capté par la source VBAN
Intégration dans l'interface d'un moyen d'associer un webhook pour chaque source (micro, RTSP, VBAN)
Enregistrement automatique des paramètres quand on clique sur "Démarrer la détection" sans avoir à cliquer sur le bouton "enregistrer les paramètres"

## Plan d'action pour l'enregistrement automatique des paramètres

1. Modification de l'interface [OK]
   - Supprimer le bouton "Enregistrer les paramètres" devenu redondant [OK]
   - Adapter les messages de feedback utilisateur [OK]
   - Faire en sorte que le bouton "Démarrer la détection" se change en "Arrêter la détection" lorsqu'on clique dessus pour lancer la détection. [OK]
   - Dans la liste des sources audio, il faut garder uniquement ce qui capte du son

2. Modification du backend [OK]
   - Fusionner la logique d'enregistrement des paramètres avec celle du démarrage de la détection [OK]
   - Faire en sorte que la détection s'arrête quand on clique sur "Arrêter la détection" [OK]
   - Ajouter une validation des paramètres avant le démarrage [OK]
   - Gérer les cas d'erreur lors de l'enregistrement [OK]

3. Tests et validation [  ]
   - Vérifier que les paramètres sont correctement sauvegardés au démarrage [OK]
   - Tester les cas d'erreur (paramètres invalides, problèmes d'écriture fichier) [OK]
   - Valider que l'arrêt de la détection ne modifie pas les paramètres

4. Documentation [  ]
   - Mettre à jour la documentation utilisateur
   - Documenter les changements dans le code