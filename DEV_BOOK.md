# DEV BOOK

Ce document explique la progression dans le développement du projet. Quand une étape est franchie, elle est marquée comme [OK]

Description du projet : ClapTrap est un service capable de reconnaitre, grâce à l'IA, des sons en provenance de différentes sources. Ces sources sont : microphone, RTSP, VBAN. A chaque source peut-être rattaché un webhook (une url). Si la source n'a pas de webhook attaché, aucun webhook n'est appelé.

# Etapes

Listing des sources audio micro [OK]
Listing des sources audio VBAN [OK]
Listing des sources RTSP via un fichier de configuration settings.json [OK]
Détection des claps à partir du son capté par le micro [OK]
Détection des claps à partir du son capté par la source RTSP [OK]
Détection des claps à partir du son capté par la source VBAN [OK]
Intégration dans l'interface d'un moyen d'associer un webhook pour chaque source (micro, RTSP, VBAN) [OK]
Enregistrement automatique des paramètres quand on clique sur "Démarrer la détection" sans avoir à cliquer sur le bouton
"enregistrer les paramètres" [OK]

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

1. Modification du modèle de données [OK]
   - Définir la structure pour stocker les webhooks dans settings.json [OK]
   - Ajouter un champ webhook_url pour chaque type de source [OK]
   - Mettre à jour la validation des paramètres [OK]

2. Mise à jour de l'interface utilisateur
   - Ajouter de l'interface pour le webhook pour chaque source [OK]
     * Section Microphones [OK]
       + Ajouter un champ webhook global unique pour tous les micros [OK]
       + Déplacer la liste de sélection des micro (Source Audio) à côté de Microphone au niveau de la section webhook [OK]
       + Dans cette Source Audio, nafficher que les micro du systeme. [OK]
       + Faire apparaitre l'icone des mains quand un clap est détecté [OK]
       + Lister les sons captés par le micro. [OK]
       + Ajouter des radio buttons pour la sélection du micro actif [OK]
       + Quand le radio bouton est OFF, le son en provenance de cette source ne doit pas être capté. [OK]
       + Masquer les champs webhook pour les micros inactifs [OK]
     * Section VBAN
       + réalisation d'un proto utilisant pyVBAN pour lister les sources vban émettrices. [OK]
       + Ajouter une section VBAN qui liste les sources VBAN disponibles en train d'émettre. [OK]
       + Permettre l'ajout/suppression dynamique des sources VBAN qu'on veut garder
         * Modification du modèle de données [OK]
           - Ajouter une section "saved_vban_sources" dans settings.json [OK]
           - Stocker pour chaque source : nom, ip, port, webhook_url, stream_name, enabled [OK]
         
         * Interface utilisateur [OK]
           - Afficher deux listes distinctes : [OK]
             > Sources VBAN détectées (actuellement émettant)
             > Sources VBAN sauvegardées (configuration permanente)
           - Ajouter un bouton "+" à côté de chaque source détectée [OK]
           - Ajouter un bouton "-" à côté de chaque source sauvegardée [OK]
           - Ajouter un champ webhook_url pour chaque source sauvegardée [OK]
           - Ajouter un switch enabled/disabled pour chaque source sauvegardée [OK]
         
         * Backend [OK]
           - Créer une route POST /api/vban/save pour sauvegarder une nouvelle source [OK]
           - Créer une route DELETE /api/vban/remove pour supprimer une source [OK]
           - Créer une route PUT /api/vban/update pour mettre à jour les paramètres [OK]
           - Implémenter la persistance dans settings.json [OK]
           - Gérer la validation des données [OK]
         
         * Tests et validation [OK]
           - Tester l'ajout d'une nouvelle source [OK]
           - Tester la suppression d'une source [OK]
           - Tester la mise à jour des paramètres [OK]
           - Vérifier la persistance après redémarrage [OK]
           - Valider la gestion des doublons [OK]
         
     * Section RTSP
       + Ajouter un champ webhook pour chaque flux RTSP [OK]
       + Permettre l'ajout/suppression des flux [OK]
       + Afficher le statut de connexion pour chaque flux [OK]
   - Ajouter une validation basique du format URL [OK]
   - Ajouter une icône ou un bouton de test du webhook [OK]

3. Implémentation du backend
   - Créer une fonction de validation des URLs webhook [OK]
   - Implémenter la sauvegarde des webhooks dans settings.json [OK]
   - Développer la logique d'appel des webhooks lors de la détection [OK]
   - Ajouter une route API pour tester les webhooks [OK]
   - Gérer les timeouts et les erreurs d'appel webhook [OK]

4. Tests et validation
   - Tester la sauvegarde et le chargement des webhooks [OK]
   - Vérifier la validation des URLs [OK]
   - Tester les appels webhook avec différents scénarios [OK]
   - Valider la gestion des erreurs [OK]
   - Tester la performance avec plusieurs webhooks actifs [OK]

## Plan d'action pour la détection des claps VBAN

1. Préparation de l'infrastructure audio [OK]
   - Créer une classe `VBANAudioProcessor` pour gérer le traitement audio des flux VBAN
     * Structure de la classe [OK]
       + Initialisation avec paramètres (ip, port, stream_name, webhook_url) [OK]
       + Configuration audio (sample_rate, buffer_size, format) [OK]
       + Gestion de l'état interne (is_running, last_clap_time) [OK]
       + Initialisation du classificateur et détecteur [OK]
     
     * Méthodes principales [OK]
       + start() : démarrage du traitement audio [OK]
       + stop() : arrêt du traitement [OK]
       + audio_callback() : traitement des données audio reçues [OK]
     
     * Méthodes utilitaires [OK]
       + initialize_classifier() : configuration du modèle YAMNet [OK]
       + preprocess_audio() : préparation des données pour le classificateur [OK]
       + detect_claps() : détection et notification des claps [OK]
     
     * Tests et validation [OK]
       + Tester la réception des flux VBAN [OK]
       + Valider la détection des claps [OK]
       + Vérifier les notifications (websocket et webhook) [OK]
       + Tests de performance et stabilité [OK]

   - Implémenter la réception et le décodage du flux audio VBAN en temps réel [OK]
     * Décodage des données brutes VBAN en tableau NumPy [OK]
     * Normalisation des valeurs audio [OK]
     * Gestion des erreurs de décodage [OK]
     * Traitement des données en temps réel [OK]
   - Mettre en place un buffer circulaire pour stocker les échantillons audio [OK]

2. Implémentation de la détection [TODO]
   - Adapter l'algorithme de détection des claps existant (celui utilisé pour le micro) [OK]
   - Implémenter le traitement du signal audio :
     * Filtrage du signal [OK]
     * Détection des pics d'amplitude [OK]
     * Analyse des caractéristiques temporelles et fréquentielles [OK]
   - Ajouter des seuils de détection configurables [OK]

3. Intégration dans l'architecture existante [OK]
   - Créer un gestionnaire de détection pour chaque source VBAN active [OK]
   - Intégrer la détection dans la boucle principale de traitement [OK]
   - Implémenter la gestion des événements de détection [OK]

4. Interface utilisateur [TODO]
   - Ajouter des indicateurs visuels de détection pour chaque source VBAN [TODO]
   - Implémenter un retour visuel lors de la détection d'un clap [TODO]
   - Ajouter des contrôles pour ajuster les paramètres de détection [TODO]

5. Tests et validation [TODO]
   - Tester la détection avec différentes sources VBAN [TODO]
   - Valider la précision de la détection [TODO]
   - Optimiser les performances et la latence [TODO]
   - Tester la robustesse face aux faux positifs [TODO]
