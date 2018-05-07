############################################################################
# Ce fichier contient tous les paramètres de l'application #
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
# Étudiant en CPES
coef_cpes = {'Première':6, 'Terminale':6, 'EAF':3, 'cpes':2}
# Autre
coef_term = {'Première':6, 'Terminale':8, 'EAF':3, 'cpes':False}
# Proportion écrit dans moyenne EAF
prop_ecrit_EAF = 2./3
#Proportion 1er trim dans moyenne Terminale (pour les élèves en terminale)
prop_prem_trim = .45

############################################################################
# Liste des motivations de la commission ...                               #
# Ne pas dépasser 5 lignes pour que l'affichage sur navigateur soit beau   # 
############################################################################
motivations = [
    "Niveau en LV",
    "Niveau en sport",
    "Établissement",
    "Age",
    "Aptitude/Attitude face au travail",
    "Discipline/Absences",
    "Dossier incomplet ou dont l'évaluation est irréalisable"
    ]

###########################################################################
# Liste des corrections accordées aux jurys...                            #
# Attention à faire en sorte que 0 soit dans la liste !!!                 #
###########################################################################
min_correc = -3 # correction minimale
max_correc = +3 # correction maximale
nb_correc = 4 # inverse du pas de la correction (vaut 4 si on fonctionne par 1/4 de point)

############################################################################
# Filières, nombre de jurys par filière	et nombre de classés par filière   #
############################################################################
filieres = ['mpsi','pcsi','cpes']
nb_Jurys = ['3','3','2']
nb_Classes  = ['120', '140', '1000']
nb_jurys = dict(zip(filieres, nb_Jurys))
nb_classes = dict(zip(filieres, nb_Classes))

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
