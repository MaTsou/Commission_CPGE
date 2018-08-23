############################################################################
# Ce fichier contient les paramètres propres à une commission              #
############################################################################

############################################################################
# Filières, nombre de jurys par filière	et nombre de classés par filière   #
############################################################################
filieres = ['mpsi','pcsi','cpes']
nombre_de_jurys = ['3','3','2']
nombre_de_candidats_classes  = ['120', '140', '1000']

############################################################################
# Liste des motivations de la commission ...                               #
# Sous la forme d'un tableau à 2 colones.                                  #
# Ne pas dépasser 7 lignes pour que l'affichage sur navigateur soit beau   # 
############################################################################
motivations = [
    ["Niveau en LV", "Harmonisation de la notation"],
    ["Niveau en sport", "Aptitude/Attitude face au travail"],
    ["Age", "Évolution"],
    ["Établissement", "Comportement"],
    ]

############################################################################
# Tableaux à générer en fin de commission                                  #
# Ces dictionnaires ont pour clés les noms de fichiers et pour arguments   #
# Les listes d'entêtes.
############################################################################
tableaux_candidats_classes = {\
    'classes' :
        ['Rang brut', 'Rang final', 'Nom', 'Prénom', 'Date de naissance',
            'Score brut', 'Correction', 'Score final', 'Jury', 'Motifs'
        ],\
    'classes_BdE' :
        ['Rang final', 'Nom', 'Prénom', 'Date de naissance']\
}

tableaux_tous_candidats = {\
    'alphabétique' :
        ['Rang brut', 'Rang final', 'Candidatures', 'Nom', 'Prénom',
            'Date de naissance', 'Sexe', 'Nationalité', 'Num ParcoursSup',
            'Boursier', 'Boursier certifié', 'Classe actuelle', 'Établissement', 'Commune',
            'Mathématiques Terminale trimestre 1', 'Physique/Chimie Terminale trimestre 1',
            'Mathématiques Terminale trimestre 2', 'Physique/Chimie Terminale trimestre 2',
            'Mathématiques Terminale trimestre 3', 'Physique/Chimie Terminale trimestre 3',
            'Mathématiques Première trimestre 1', 'Physique/Chimie Première trimestre 1',
            'Mathématiques Première trimestre 2', 'Physique/Chimie Première trimestre 2',
            'Mathématiques Première trimestre 3', 'Physique/Chimie Première trimestre 3',
            'Écrit EAF', 'Oral EAF', 'Mathématiques CPES', 'Physique/Chimie CPES',
            'Score brut', 'Correction', 'Score final', 'Jury', 'Motifs'
        ]\
}

###### Ne pas toucher les lignes suivantes, elles préparent les paramètres
# pour le programme...                                              ######
nb_jurys = dict(zip(filieres, nombre_de_jurys))
nb_classes = dict(zip(filieres, nombre_de_candidats_classes))
