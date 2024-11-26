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
Enregistrement automatique des paramètres quand on clique sur "Démarrer la détection" sans avoir à cliquer sur le bouton "enregistrer les paramètres" [OK]

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

3. Tests et validation [OK]
   - Vérifier que les paramètres sont correctement sauvegardés au démarrage [OK]
   - Tester les cas d'erreur (paramètres invalides, problèmes d'écriture fichier) [OK]
   - Valider que l'arrêt de la détection ne modifie pas les paramètres [OK]

4. Documentation [OK]
   - Mettre à jour la documentation utilisateur [OK]
   - Documenter les changements dans le code [OK]

## Plan d'action pour l'intégration des webhooks

1. Modification du modèle de données
   - Définir la structure pour stocker les webhooks dans settings.json [OK]
   - Ajouter un champ webhook_url pour chaque type de source [OK]
   - Mettre à jour la validation des paramètres [OK]

2. Mise à jour de l'interface utilisateur
   - Ajouter de l'interface pour le webhook pour chaque source
     * Section Microphones
       + Ajouter un champ webhook global unique pour tous les micros [OK]
       + Déplacer la liste de sélection des micro (Source Audio) à côté de Microphone au niveau de la section webhook
       + Dans cette Source Audio, nafficher que les micro du systeme.
       + Ajouter des radio buttons pour la sélection du micro actif
       + Masquer les champs webhook pour les micros inactifs
     * Section VBAN
       + Ajouter un champ webhook pour chaque source VBAN
       + Permettre l'ajout/suppression dynamique des sources
       + Afficher le statut de connexion pour chaque source
     * Section RTSP
       + Ajouter un champ webhook pour chaque flux RTSP
       + Permettre l'ajout/suppression des flux
       + Afficher le statut de connexion pour chaque flux
   - Ajouter une validation basique du format URL
   - Ajouter une icône ou un bouton de test du webhook
   - Ajouter des tooltips explicatifs sur le format attendu
   - Griser les éléments quand la détection est lancée.

3. Implémentation du backend
   - Créer une fonction de validation des URLs webhook
   - Implémenter la sauvegarde des webhooks dans settings.json
   - Développer la logique d'appel des webhooks lors de la détection
   - Ajouter une route API pour tester les webhooks
   - Gérer les timeouts et les erreurs d'appel webhook

4. Tests et validation
   - Tester la sauvegarde et le chargement des webhooks
   - Vérifier la validation des URLs
   - Tester les appels webhook avec différents scénarios
   - Valider la gestion des erreurs
   - Tester la performance avec plusieurs webhooks actifs

5. Documentation
   - Documenter le format des requêtes webhook
   - Mettre à jour la documentation utilisateur
   - Ajouter des exemples d'intégration
   - Documenter les codes d'erreur possibles
   - Mettre à jour les commentaires dans le code

6. Déploiement et monitoring
   - Ajouter des logs pour les appels webhook
   - Mettre en place un système de retry en cas d'échec
   - Implémenter des métriques de succès/échec
   - Prévoir un mécanisme de désactivation d'urgence