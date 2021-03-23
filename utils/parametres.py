############################################################################
# Ce fichier contient les paramètres stables de l'application              #
############################################################################

# Entête général des pages html:
entete = 'EPA - Recrutement CPGE/CPES'

############################################################################
# Coefficients pour le calcul des scores bruts                             #
############################################################################
# Étudiant en terminale
coef_term = {\
        'Mathématiques Spécialité Première trimestre 1' : 1.5,
        'Mathématiques Spécialité Première trimestre 2' : 1.5,
        'Mathématiques Spécialité Première trimestre 3' : 0,
        'Physique-Chimie Spécialité Première trimestre 1' : 1.5,
        'Physique-Chimie Spécialité Première trimestre 2' : 1.5,
        'Physique-Chimie Spécialité Première trimestre 3' : 0,
        'Mathématiques Spécialité Terminale trimestre 1' : .4*1.8,
        'Mathématiques Expertes Terminale trimestre 1' : .6*1.8,
        'Mathématiques Spécialité Terminale trimestre 2' : .4*2.2,
        'Mathématiques Expertes Terminale trimestre 2' : .6*2.2,
        'Physique-Chimie Spécialité Terminale trimestre 1' : 1.8,
        'Physique-Chimie Spécialité Terminale trimestre 2' : 2.2,
        'Écrit EAF' : 0,
        'Oral EAF' : 0
}

# Étudiant en CPES
coef_cpes= {\
        'Mathématiques Spécialité Première trimestre 1' : 1,
        'Mathématiques Spécialité Première trimestre 2' : 1,
        'Mathématiques Spécialité Première trimestre 3' : 1,
        'Physique-Chimie Spécialité Première trimestre 1' : 1,
        'Physique-Chimie Spécialité Première trimestre 2' : 1,
        'Physique-Chimie Spécialité Première trimestre 3' : 1,
        'Mathématiques Spécialité Terminale trimestre 1' : .4*1.8,
        'Mathématiques Expertes Terminale trimestre 1' : .6*1.8,
        'Mathématiques Spécialité Terminale trimestre 2' : .4*2.2,
        'Mathématiques Expertes Terminale trimestre 2' : .6*2.2,
        'Mathématiques Spécialité Terminale trimestre 3' : 0,
        'Mathématiques Expertes Terminale trimestre 3' : 0,
        'Physique-Chimie Spécialité Terminale trimestre 1' : 1.8,
        'Physique-Chimie Spécialité Terminale trimestre 2' : 2.2,
        'Physique-Chimie Spécialité Terminale trimestre 3' : 0,
        'Écrit EAF' : 0,
        'Oral EAF' : 0,
        'Mathématiques CPES' : 0,
        'Physique/Chimie CPES' : 0
}

###########################################################################
# Liste des corrections accordées aux jurys...                            #
# Attention à faire en sorte que 0 soit dans la liste !!!                 #
###########################################################################
min_correc = -3 # correction minimale
max_correc = +4 # correction maximale
nb_correc = 4 # inverse du pas de la correction (vaut 4 si on fonctionne par 1/4 de point)
