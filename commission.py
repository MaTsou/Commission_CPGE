#!/usr/bin/env python3
#-*- coding: utf-8 -*-

################################################
#        Description de l'application          #
################################################
# Les différentes tâches de cette application sont découpées en autant d'objets, 
# chacun étant défini dans un fichier qui porte le nom de la classe qu'il 
# contient. Tous ces fichiers se trouvent dans le répertoire 'utils' : 

# * 'Serveur' : classe instanciée par le programme principal et qui a pour seule 
# mission de gérer les interactions avec les navigateurs connectés (fournir les 
# pages html et recevoir les formulaires). Il se charge de solliciter les autres 
# organes du programme pour traiter les formulaires ou fabriquer les pages 
# réponses.
#
# * 'Composeur' : classe dont l'unique tâche est de construire les pages html (à 
# la demande de 'Serveur'). Elle se sert d'un fichier 'patrons.html' qui 
# contient les différents modèles (template) de pages. 'Composeur' utilise la 
# méthode .format() des objets de type string pour remplir ces modèles avec les 
# données appropriées. 'composeur.py' et 'patrons.html' sont les seuls fichiers 
# contenant du code html. L'idée est d'encapsuler la génération des pages html.  
# 
# Nouveauté 2021 : la classe 'Fichier' ci-dessous a été scindée; une partie de 
# son "travail" est maintenant effectué par les instances de la classe 'Candidat'
#
# * 'Fichier' : classe dont l'unique tâche consiste à manipuler des fichiers xml 
# existants. Lecture, écriture. Un des attribut principal de cette classe est un 
# dictionnaire (dont le nom est 'acces'). Ce dictionnaire se charge de traduire 
# une requête (quel est la date de naissance de ce candidat, etc.) venant d'un 
# autre organe de l'application (voir clients ci-dessous) en une requête xpath. 
# L'intérêt est que toute modification de l'arborescence des fichiers xml 
# (arborescence décidée dans la bibliothèque csv_parcourssup.py) ne nécessitera 
# qu'une mise à jour du dictionnaire 'acces' pour que l'application fonctionne 
# ET si jamais le format de fichier xml devait être abandonné au profit d'un 
# autre (bdd, ...), seule la classe 'Fichier' devra être réécrite. L'idée est 
# d'encapsuler la manipulation des fichiers.
#
# * 'Clients' : classe dont l'unique tâche est de contenir les méthodes des 
# différents clients qui vont se connecter au serveur. En fait, ce qui va servir 
# sont les deux classes filles de clients :
#       * 'Admin' : il s'agit du client qui se trouve sur la machine exécutant 
#       le serveur. Cet administrateur du recrutement gère tout ce qui est 
#       administratif. En amont de la commission, il prépare les dossiers 
#       (complétion de dossiers, filtrage de dossiers non recevables), 
#       génération des fichiers que chaque jury devra traiter. En aval de la 
#       commission, il récupère et synthétise les décisions des 'jurys', produit 
#       des fiches bilan de commission ainsi que des tableaux récapitulatifs).
#
#       * 'Jury' : membre de la commission de recrutement. Analyse et classe les 
#       dossiers qui lui sont présentés.
#
# De nombreux paramètres sont disponibles, les uns dans le fichier 'config.py' 
# du répertoire principal, les autres dans le fichier 'parametres.py' dans le 
# répertoire 'utils'. Ce découpage a été choisi pour qu'une personne non formée 
# au langage python puisse avoir accès à quelques paramètres (dont la syntaxe 
# est suffisamment simple).

import os, sys, cherrypy, logging, socket
from tkinter import *
from utils.toolbox import restaure_virginite
from utils.serveur import Serveur

########################################################################
#                    === PROGRAMME PRINCIPAL ===                       #
########################################################################

""" Le programme principal lance un gestionnaire (cherrypy) de serveur (ici
sous la forme d'une instance d'un objet "Serveur").

Le lancement de ce programme peut se faire par double clic sur son icone : 
lancement standard, sans option.
ou en ligne de commande 'python commission.py'. Il est alors possible de 
préciser certaines options :
  -jury : lance le programme en forçant un client type jury sur la machine 
  serveur
  -clean-logs : efface les fichiers log
  -log XXX : précise le niveau souhaité dans les messages log. (par défaut INFO, 
  pourrait être DEBUG...)
"""

##### Début du code :
### Configuration d'un logger (gestionnaire d'un fichier log)
# Deux options s'offrent :
# - soit on passe le logger (l'instance journal) à tous les objets de 
# l'application.
# - soit on passe le handler (en gros le fichier qui reçoit le journal) et 
# chaque objet a son propre logger ; intérêt = gérer les seuils de message 
# indépendamment...
#
def standard_logger(name, path, formatter_string):
    formatter = logging.Formatter(formatter_string)
    # Qui récupère les messages ? (on peut en définir plusieurs)
    handler = logging.FileHandler(path, mode="a", encoding="utf-8")
    handler.setFormatter(formatter)
    # L'objet appelé par tout élément du programme qui veut journaliser qqc
    journal = logging.getLogger(name)
    journal.addHandler(handler)
    return journal

def configure_loggers(log_path):
    journaux = []
    # Création d'un journal de log pour la commission
    comm_log = standard_logger('commission',\
            os.path.join(log_path, 'journal.log'),\
            "%(asctime)s :: %(levelname)s :: %(message)s")
    journaux.append(comm_log)

    # Création d'un journal de log pour le nettoyage
    nett_log = standard_logger('nettoie_xml',\
            os.path.join(log_path, 'journal_nettoie.log'),\
            "%(levelname)s :: %(message)s")
    journaux.append(nett_log)
    return journaux

# Récupération et gestions des options de lancement :
# '-jury' pour une version jury,
# '-clean-logs' pour nettoyer les fichiers log 
# '-log xxxx' pour spécifier le niveau des messages log
jury = '-jury' in sys.argv

log_path = os.path.join("utils", "logs")
if '-clean-logs' in sys.argv:
    restaure_virginite(log_path)

# configuration des loggers
journaux = configure_loggers(log_path)

default_log_level = 'INFO'
if '-log' in sys.argv:
    log_level = sys.argv[sys.argv.index('-log')+1]
for journal in journaux:
    try:
        journal.setLevel(getattr(logging, log_level.upper()))
    except:
        journal.setLevel(getattr(logging, default_log_level))

### Gestion de l'ip sur laquelle sera servie l'application
def get_ip():
    # Obtenir l'adresse ip sur le réseau local
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    IP = ['127.0.0.1']
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP_ext = s.getsockname()[0]
    except Exception:
        IP_ext = none
    finally:
        IP.append(IP_ext)
        s.close()
    return IP

# On récupère la liste des ip disponibles
ip_list = get_ip()
# Si cette liste contient plus d'un élément,
# un menu est proposé pour choisir l'ip 
def submit():
    ws.destroy()

if len(ip_list) > 1:
    ws = Tk()
    ws.title("Choix de l'ip")
    ws.geometry('400x150')
    frame = LabelFrame(ws, \
            text="Choisissez l'ip sur laquelle servir l'application :")
    frame.pack(pady=15)
    var = IntVar()
    for index, ip in enumerate(ip_list):
        if index:
            txt = "indispensable pour la commission"
        else:
            txt = "recommandé pour l'administration"
        Radiobutton(frame, text=f"{ip} ({txt})", variable=var, value=index,)\
                .grid(row=index, column=1)
    Button(ws, text="Valider", command=submit, padx=15, pady=5).pack(pady=10)
    ws.mainloop()
    ip = ip_list[var.get()]
else:
    ip = ip_list[0]

# Reconfiguration et démarrage du serveur web :
cherrypy.config.update({"tools.staticdir.root":os.getcwd()})
cherrypy.config.update({"server.socket_host":ip})
cherrypy.quickstart(Serveur(jury, ip),'/', config ="utils/cherrypy.conf")
