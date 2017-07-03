############################################################################
# Ce fichier contient tous les paramètres de l'application "Commission.py" #
############################################################################

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
motifs = []
motifs.append('Niveau particulièrement élevé/faible en')
motifs.append('Harmonisation du score brut')
motifs.append('Aptitude/Attitude face au travail')
motifs.append('Discipline/Absences')
motifs.append('Dossier incomplet ou moins bon que le dernier classé')


###########################################################################
# Liste des corrections accordées aux jurys...                            #
# Attention à faire en sorte que 0 soit dans la liste !!!                 #
###########################################################################
min_correc = -3 # correction minimale
max_correc = +3 # correction maximale
nb_correc = 4 # inverse du pas de la correction (vaut 4 si on fonctionne par 1/4 de point)

###########################################################################
# Filières et nombre de jury par filière				  #
# Attention : si modification des filères, il y aura des pb dans les stat #
###########################################################################
filieres = ['mpsi','pcsi','cpes']
nb_jury = {'mpsi':'3','pcsi':'3','cpes':'2'}
