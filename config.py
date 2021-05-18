############################################################################
# Ce fichier contient les paramètres propres à une commission              #
############################################################################

############################################################################
# Filières, nombre de jurys par filière et nombre de classés par filière   #
# Pour classer tous les candidats traités, il suffit d'indiquer 'tous' .   #
############################################################################
filieres = ['mpsi','pcsi','cpes']
nombre_de_jurys = ['3','3','1']
nombre_de_candidats_classes  = ['160', '300', 'tous']

############################################################################
# Liste des motivations de la commission ...                               #
############################################################################
motivations = [
    "Niveau en LV",
    "Harmonisation de la notation",
    "Niveau en sport",
    "Comportement",
    "Aptitude/Attitude face au travail",
    "Age",
    "Évolution",
    "Établissement",
    ]

############################################################################
# Tableaux à générer en fin de commission                                  #
# Ces dictionnaires ont pour clés les noms de fichiers et pour arguments   #
# Les listes d'entêtes.
############################################################################
tableaux_candidats_classes = {\
    'classes' :
        ['Rang brut', 'Rang final', 'Nom', 'Prénom', 'Date de naissance',
            'Num ParcoursSup', 'Boursier', 'Boursier certifié', 'Score brut',
            'Correction', 'Score final', 'Jury', 'Motifs'
        ],\
    'classes_BdE' :
        ['Rang final', 'Nom', 'Prénom', 'Date de naissance', 'Num ParcoursSup'
        ]\
}

tableaux_tous_candidats = {\
    'alphabétique' :
        ['Rang brut', 'Rang final', 'Candidatures', 'Nom', 'Prénom',
            'Date de naissance', 'Sexe', 'Nationalité', 'Num ParcoursSup',
            'Boursier', 'Boursier certifié', 'Classe actuelle', 'Établissement', 'Commune',
            'Mathématiques Spécialité Terminale trimestre 1', 
            'Mathématiques Expertes Terminale trimestre 1', 
            'Physique-Chimie Spécialité Terminale trimestre 1',
            'Mathématiques Spécialité Terminale trimestre 2', 
            'Mathématiques Expertes Terminale trimestre 2', 
            'Physique-Chimie Spécialité Terminale trimestre 2',
            'Mathématiques Spécialité Terminale trimestre 3', 
            'Mathématiques Expertes Terminale trimestre 3', 
            'Physique-Chimie Spécialité Terminale trimestre 3',
            'Mathématiques Spécialité Première trimestre 1', 
            'Physique-Chimie Spécialité Première trimestre 1',
            'Mathématiques Spécialité Première trimestre 2', 
            'Physique-Chimie Spécialité Première trimestre 2',
            'Mathématiques Spécialité Première trimestre 3', 
            'Physique-Chimie Spécialité Première trimestre 3',
            'Écrit EAF', 'Oral EAF', 'Mathématiques CPES', 'Physique/Chimie CPES',
            'Score brut', 'Correction', 'Score final', 'Jury', 'Motifs'
        ]\
}

###### Ne pas toucher les lignes suivantes, elles préparent les paramètres
# pour le programme...                                              ######
nb_jurys = dict(zip(filieres, nombre_de_jurys))
nb_classes = dict(zip(filieres, nombre_de_candidats_classes))
