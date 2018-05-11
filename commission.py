#!/usr/bin/env python3
#-*- coding: utf-8 -*-

##### Principe de l'application ####
# Le programme principal lance un gestionnaire de serveur. Il se présente sous la forme d'une instance d'un objet 
# "Serveur". Cet objet dispose d'un attribut qui est un dictionnaire d'instances d'objets "Client". Ceci afin 
# d'identifier qui dépose telle ou telle requête.
#
# Les clients sont ici de 2 types : soit de type administrateur, soit de type jury. Chacun est héritier d'une classe 
# plus générale : "Client". En effet, admin et jury partagent certaines caractéristiques, parce que ce sont tous deux 
# des clients du serveur. Cependant, les actions qu'ils peuvent exécutés étant différentes, il a fallu distinguer ces 
# objets. Notamment dans le traitement d'un dossier de candidature, l'administrateur peut compléter certaines infos 
# (notes notamment) manquantes mais ne juge pas le dossier alors qu'un jury corrige le score brut, commente son choix, 
# mais ne touche pas au contenu du dossier.


import os, sys, cherrypy
from utils.serveur import Serveur

########################################################################
#                    === PROGRAMME PRINCIPAL ===                       #
########################################################################

# Récupération des options de lancement ('-test' pour une version test, '-ip 196.168.1.10' pour changer l'ip serveur)
test = False
if '-test' in sys.argv:
    test = True

ip = '127.0.0.1' # ip socket_host par défaut...
if '-ip' in sys.argv:
    ip = sys.argv[sys.argv.index('-ip')+1]

# Reconfiguration et démarrage du serveur web :
cherrypy.config.update({"tools.staticdir.root":os.getcwd()})
cherrypy.config.update({"server.socket_host":ip})
cherrypy.quickstart(Serveur(test, ip),'/', config ="utils/cherrypy.conf")
