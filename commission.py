#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os, sys, cherrypy
from utils.serveur import Serveur

########################################################################
#                    === PROGRAMME PRINCIPAL ===                       #
########################################################################

""" Le programme principal lance un gestionnaire (cherrypy) de serveur (ici
sous la forme d'une instance d'un objet "Serveur").

Le lancement de ce programme peut se faire par double clic sur son icone : lancement standard, sans option.
ou en ligne de commande 'python commission.py'. Il est alors possible de préciser certaines options :
  -test : lance une version test du programme (un menu supplémentaire est alors disponible)
  -ip x.x.x.x : lance le serveur sur une ip non locale (sert au moment de la commission,
    tout le reste se fait en local) """

# Début du code :
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
