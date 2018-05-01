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
# Filières et nombre de jurys par filière				                   #
############################################################################
filieres = ['mpsi','pcsi','cpes']
nb_jurys = ['3','3','2']
nb_jury = dict(zip(filieres, nb_jurys))
