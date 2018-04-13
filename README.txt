--- Gestion_Commission_EPA ---
Procédure d'utilisation du programme d'aide au recrutement : 

############### Récupération des données ParcoursSUP ############
--> Enregistrer dans le dossier "data" les fichiers suivants en provenance de ParcoursSUP :
	- Fichiers .csv contenant toutes les informations des candidats\
		Notamment : dans la rubrique bulletins, cocher toutes les infos d'entêtes (Niveau de formation, Filière, ...)
	- Fichiers .pdf contenant le dossier du candidat (au min. bulletins et fiche de candidature)

################## Utilisation du programme #####################
--> Lancer le programme commission.py (double clic)

--> Le navigateur doit s'ouvrir automatiquement et afficher la page d'accueil

######################### Information ###########################
** Différents paramètres de l'application sont modifiables.
Ils se trouvent dans le fichier parametres.py situé dans le dossier utils.


################# Pour la commission en réseau ###################
Opération à effectuer par une personne compétente !
Ci-dessous, x.x.x.x représente l'adresse ip de la machine ayant le rôle de serveur.

En ligne de commande taper "python commission.py -ip x.x.x.x"
Chaque client accèdera au serveur à l'URL : x.x.x.x:8080
