---------------------------------------
--- Gestion recrutement ParcoursSup ---
---------------------------------------

# Procédure d'installation :
1. Installation Python 3.6 (ou supérieur) et les bibliothèques nécessaires :

  + Télécharger (puis lancer) depuis le site python.org, menu donwloads, un 
  installeur python3.6 (les meilleurs résultats ont été obtenus avec 
  l'installeur 'webbased'. Bien vérifier que l'option 'PIP' et l'option 'ajouter 
  à la variable PATH' soient sélectionnées).
  + En ligne de commande, lancer les commandes suivantes pour installer les 
  bibliothèques utiles :
    * python -m pip install --upgrade cherrypy
    * python -m pip install --upgrade parse
    * python -m pip install --upgrade lxml
    * python -m pip install --upgrade PyPDF2

2. Installation de l'application proprement dite :
Il suffit de télécharger le programme qui se trouve 
[ICI](https://github.com/MaTsou/Gestion_Commission_EPA) dans le dossier de son 
choix.

-------------------------------------------------
# Principe de la procédure de recrutement proposée par cette application :
Une fois récupérées les données proposées par ParcoursSup, 3 phases se succèdent 
:
1. Préparation de la commission par **L'administrateur** (nom utilisé dans 
l'application pour désigner le reponsable du recrutement) du recrutement. Cette 
phase aboutit à un pré-classement des candidats dans l'ordre d'un _score_ dit 
brut.

2. Commission de recrutement. Elle a lieu en réseau et est faite par des jurys. 
Chaque jury analyse les dossiers qui lui sont soumis et apporte au besoin une 
correction (motivée) au score brut. Les candidatures obtiennent alors un _score 
final_.

3. Clôture de l'opération de recrutement. Opération effectuée par 
l'administrateur. Récupération des scores finals et classement. Pour que les 
différences d'appréciation entre des jurys différents n'interviennent pas, la 
procédure consiste à classer les candidats de chaque jury puis à construire la 
pile finale en dépilant successivement les piles jury (jury1, jury2, jury3, 
jury1, jury2, jury3, etc.). Différents documents sont alors produits : une fiche 
par candidat classé résume le traitement reçu, plusieurs tableaux 
(configurables) qui contiennent le bilan de commission.

## Différents paramètres de l'application sont modifiables.
1. Les uns se trouvent dans le fichier `config.py` (répertoire racine) : 
  * liste des filières, liste des nombres de jurys par filière, liste des 
    nombres de candidats à classer par filière,
  * liste de valeurs pré-définies pour les motivations des jurys,
  * Définitions des tableaux à générer en phase 3.
2. Les autres se trouvent dans le fichier `parametres.py` (répertoire 
    `utils`) : 
  * Entête personnalisée pour les pages html,
  * coefficients intervenant dans le calcul du score brut (deux cas : 
        coefficients concernant les candidats actuellement en terminale; 
        coefficients concernant les candidats actuellement en CPES),
  * intervalle de correction proposé aux jurys (min, max, intervalle).

      -------------------------------------------------
# Utilisation du programme d'aide au recrutement : 

## Récupération des données ParcoursSUP
Enregistrer dans le dossier `data` les fichiers suivants en provenance de 
ParcoursSUP :

  + Fichiers .csv contenant toutes les informations des candidats
  Notamment : dans la rubrique bulletins, cocher toutes les infos d'entêtes 
  (Niveau de formation, Filière, ...)
  + Fichiers .pdf contenant les dossiers des candidats (au min. bulletins et 
    fiche de candidature)

  Ces fichiers doivent tous contenir le nom de la filière à laquelle ils se 
  rapportent, nom tel que mentionné dans le fichier `config.py` (liste 
  _filieres_)

## Phase 1 :
  L'administrateur lance l'application par un double-clic sur `commission.py`. 
  Son navigateur par défaut s'ouvre alors automatiquement et affiche la page 
  d'accueil. Sur celle-ci, sont visibles les fichiers .csv et .pdf précédemment 
  déposés dans le répertoire `data`.
  1. Première étape : Traiter ces fichiers. En cliquant sur le bouton 
  `Vérifier/Traiter`, l'administrateur lance une procédure d'exploitation des 
  fichiers provenant de ParcoursSup. Cette procédure est longue, une page 
  indiquant la progression est proposée. Pour chaque filière, cette exploitation 
  consiste en :
    * la récupération des données utiles contenues dans le fichier .csv, suivie de 
    la création d'un fichier `admin_XXXX.xml` (XXXX désignant la filière),
    * une analyse rapide de la validité de certaines candidatures (filière 
    d'origine et validation du dossier sur ParcoursSup) ainsi que le repérage 
    des dossiers incomplets,
    * le découpage du fichier .pdf en autant de fichiers que de candidats,
    * la réalisation d'un décompte des candidatures.

  À la fin de cette opération, un bouton propose le retour au menu.

  2. Le menu est alors enrichi. Les décomptes de candidatures sont affichés 
  ainsi que les fichiers `admin_XXXX.xml` créés. Cette deuxième étape va 
  consister pour l'administrateur à préparer les dossiers pour la commission.  
  Grâce à chaque bouton `admin_XXXX.xml`, il accède à une page qui lui permet 
  de visualiser chacune des candidatures.  Dans la liste à droite figurent sur 
  fond gris les candidatures éliminées par l'analyse précédante (candidature non 
  validée ou filière inadéquate) et sur fond rouge les candidatures qui 
  nécessitent son regard avant d'être soumise à la commission.  Pour chacune des 
  candidatures sur fond rouge, le motif de l'alerte ainsi donnée à 
  l'administrateur peut être :
    * dossier incomplet : il s'agit d'une sitation ou les données nécessaires au 
      calcul du score brut n'ont pas pû être trouvées dans le fichier .csv. Dans 
    ce cas, l'administrateur peut, en consultant le dossier (lien proposé 
    au-dessus du tableau de synthèse des notes), éventuellement trouver les 
    informations manquantes et renseigner directement dans la page html les 
    champs adéquats. Remarque : un candidat noté en semestre a nécessairement 
    moins de notes qu'un candidat noté en trimestres; le dossier apparaît 
    incomplet alors qu'il ne l'est pas. Il suffit alors à l'administrateur de 
    cocher les cases (à côté du niveau `Première` ou `Terminale`) pour en tenir 
    compte et que le calcul de score brut soit juste.
    * vérifier la filière : l'analyse initiale n'a pas reconnue la filière 
    d'origine du candidat comme étant 'recevable' ou 'non recevable'. 
    L'administrateur doit, en consultant le dossier, vérifier ce point.

  Dans tous les cas, l'administrateur doit lever l'alerte. Il lui suffit, une 
  fois qu'il a fait tout son possible pour compléter un dossier, de supprimer 
  les caractères `- Alerte :` du champ de motifs et de les remplacer 
  (éventuellement) par un message à l'intention des jurys.. Ensuite, soit il 
  décide que le dossier n'est pas recevable (il clique alors sur le bouton 
  `NC`), soit qu'il l'est (il clique alors sur le bouton `Classer`).  

  Une fois que toutes les alertes sont levées, le bouton `générer les fichiers 
  commission` (menu prinipal) devient actif. En cliquant dessus, 
  l'administrateur lance une procédure qui aboutit à la génération des fichiers 
  que vont traiter les jurys. Cette procédure consiste à calculer les scores 
  bruts, puis classer par ordre de score brut décroissants et enfin répartir de 
  manière homogène la liste obtenue en autant de listes que de jurys. Fin de la 
  phase 1; le menu de l'administrateur change, il ne peut plus intervenir sur 
  les dossiers.

## Phase 2 :
  Cette phase a lieu en réseau. Toutes les machines (1 par jury + 1 pour le 
  serveur) doivent être sur un même réseau.  La machine hébergeant le serveur 
  doit disposer de la présente application. Le lancement de l'application est 
  particulier car celle-ci doit être servie sur l'adresse ip (x.x.x.x) de la 
  machine serveur. Le lancement se fait en ligne de commande :
  `python commission.py -ip x.x.x.x`
  Les clients (jurys) accèdent alors à l'application avec le navigateur de leur 
  choix à l'url `x.x.x.x:8080`
  Chaque jury trouve une page d'accueil sur laquelle tous les fichiers à traiter 
  sont listés. Chaque jury choisit le fichier qui lui a été attribué par 
  l'administrateur et commence son traitement. Les dossiers exlus par 
  l'administrateur n'apparaissent pas; les dossiers sur lesquels l'adminstrateur 
  à laissé un message apparaissent sur fond rouge. Traiter un dossier signifie :
  * soit, avoir corrigé (ou non) le score d'un dossier, avoir motivé cette 
    correction et avoir validé en cliquant sur le bouton `Classer`,
  * soit, avoir motivé un non classement et avoir cliqué sur `NC`.

  L'avancement de la commission peut être suivie sur la machine serveur. Sont 
  affichés _en temps réel_ les nombres de dossiers traités par filière. La 
  commission peut-être arrêtée à tout moment, chaque traitement étant 
  immédiatement suivi par une sauvegarde physique sur le disque de la machine 
  serveur.
  Lorsque suffisamment de dossiers ont été traités, la commission peut 
  s'arrêter. Les dossiers non vus (car trop loin dans le classement) seront 
  automatiquement traités : `NC` car `dossier moins bon que le dernier classé`.
  Fin de la phase 2.

## Phase 3 :
  L'administrateur, lançant l'application en local, va se voir proposer un menu 
  dans lequel (étape 4) il peut `Récolter` le travail de la commission. La 
  procédure de récolte consiste, pour chaque fichier de jury, à :
  * calculer tous les scores finals,
  * classer par ordre de score finals décroissants.

  Puis, pour chaque filière, à reconstituer (voir le principe exposé plus haut) 
  une liste unique à partir des listes ordonnées. Enfin, enregistrement de ces 
  listes dans les fichiers `class_XXXX.xml` et création des tableaux bilans 
  (disponibles dans le répertoire `tableaux`).

  Est alors proposée à l'administrateur une 5e étape qui consiste à imprimer, 
  pour chaque candidat retenu, une fiche récapitulative de la commission.
