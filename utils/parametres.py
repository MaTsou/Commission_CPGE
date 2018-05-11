############################################################################
# Ce fichier contient les paramètres stables de l'application              #
############################################################################

# Entête général des pages html:
entete = 'EPA - Recrutement CPGE/CPES'

############################################################################
# Coefficients pour le calcul des scores bruts                             #
# Les coefficients ci-dessous sont cumulés. La répartition est faite dans  #
# la fonction de calcul qui se trouve dans le module "interface_xml.py"    #
# Première : tous les trimestres (ou semestres) équivalents                #
# EAF : prop_ecrit_EAF pour l'écrit et le complément pour l'oral           #
# Terminale : tous équiv si CPES sinon prop_prem_trim pour 1er trim, ...   #
############################################################################
# Étudiant en terminale
coef_term = {\
        'Mathématiques Première trimestre 1' : 1,
        'Mathématiques Première trimestre 2' : 1,
        'Mathématiques Première trimestre 3' : 1,
        'Physique/Chimie Première trimestre 1' : 1,
        'Physique/Chimie Première trimestre 2' : 1,
        'Physique/Chimie Première trimestre 3' : 1,
        'Mathématiques Terminale trimestre 1' : 1.8,
        'Mathématiques Terminale trimestre 2' : 2.2,
        'Physique/Chimie Terminale trimestre 1' : 1.8,
        'Physique/Chimie Terminale trimestre 2' : 2.2,
        'Écrit EAF' : 2,
        'Oral EAF' : 1
}

coef_cpes= {\
        'Mathématiques Première trimestre 1' : 1,
        'Mathématiques Première trimestre 2' : 1,
        'Mathématiques Première trimestre 3' : 1,
        'Physique/Chimie Première trimestre 1' : 1,
        'Physique/Chimie Première trimestre 2' : 1,
        'Physique/Chimie Première trimestre 3' : 1,
        'Mathématiques Terminale trimestre 1' : 1,
        'Mathématiques Terminale trimestre 2' : 1,
        'Mathématiques Terminale trimestre 3' : 1,
        'Physique/Chimie Terminale trimestre 1' : 1,
        'Physique/Chimie Terminale trimestre 2' : 1,
        'Physique/Chimie Terminale trimestre 3' : 1,
        'Écrit EAF' : 2,
        'Oral EAF' : 1,
        'Mathématiques CPES' : 1,
        'Physique/Chimie CPES' : 1
}

###########################################################################
# Liste des corrections accordées aux jurys...                            #
# Attention à faire en sorte que 0 soit dans la liste !!!                 #
###########################################################################
min_correc = -3 # correction minimale
max_correc = +3 # correction maximale
nb_correc = 4 # inverse du pas de la correction (vaut 4 si on fonctionne par 1/4 de point)
