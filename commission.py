#!/usr/bin/env python3
#-*- coding: utf-8 -*-

# Comment cherrypy et le navigateur discutent :

# navigateur --> cherrypy : par l'intermédiaire des formulaires html. Dans la déclaration d'un formulaire,
# un choix method = POST (ou GET) action = nom_d_une_méthode_python qui sera exécutée dès la validation
# du formulaire.
# Les éléments du formulaire sont accessibles dans le dictionnaire kwargs...
# Une méthode n'est visible par le navigateur que si elle est précédée par @cherrypy.expose
#
# cherrypy --> navigateur : en retour (par la fonction return), le code python renvoi le code --- sous
# la forme d'une chaine (immense) de caractères --- d'une page html.
# Ce peut-être la même qui a généré l'appel à cette méhode ou toute autre. 
#
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


import os, sys, cherrypy, glob, webbrowser
from utils.parametres import entete
from utils.adjoint import traiter_csv, traiter_pdf, stat, generation_comm, clore_commission
# Chargement de toutes les classes dont le serveur a besoin
from utils.clients import Jury, Admin
from utils.fichier import Fichier
from utils.composeur_html import Composeur


########################################################################
#                        Class Serveur                                 #
########################################################################

class Serveur(): # Objet lancé par cherrypy dans le __main__
    "Classe générant les objets gestionnaires de requêtes HTTP"
    
    def __init__(self, test, ip):
        # constructeur
        self.clients =  {}  # dictionnaire contenant les clients connectés
        self.test = test  # booléen : version test (avec un menu "Admin or Jury ?")
        self.rafraich = False  # booléen qui sert à activer ou nom la fonction refresh
        self.comm_en_cours = (ip != '127.0.0.1')  # booléen True pendant la commission --> menu ad hoc
        self.fichiers_utilises = [] # Utile pour que deux jurys ne choisissent pas le même fichier..
        self.html_compose = Composeur(entete)
        navi = webbrowser.get()  # Quel est le navigateur par défaut ?
        navi.open_new('http://'+ip+':8080')  # on ouvre le navigateur internet, avec la bonne url..

    # Doit-on rafraichir ?
    def set_rafraich(self, bool = False):
        self.rafraich = bool

    def get_rafraich(self):
        return self.rafraich

    # Rafraîchir un client suite à un évènement Server (SSE)
    @cherrypy.expose
    def refresh(self, **kwargs):
        cherrypy.response.headers["content-type"] = "text/event-stream"
        def msg():
            yield "retry: 5000\n\n"
            if self.get_rafraich():
                self.set_rafraich(False) # On ne rafraîchit qu'une fois à la fois !
                yield "event: message\ndata: ok\n\n"
        return msg()

    # Accesseurs et mutateurs
    # Quel est le client courant ?
    def get_client_cour(self):
        return self.clients[cherrypy.session["JE"]]
    # Fin accesseurs et mutateurs

    @cherrypy.expose
    def index(self):
        # Page d'entrée du site web - renvoie une page HTML
        # S'il n'y a pas déjà un cookie de session sur l'ordinateur client, on en créé un
        if cherrypy.session.get('JE', 'none') == 'none':
            key = 'client_{}'.format(len(self.clients) + 1) # clé d'identification du client
        else: # On récupère la clé et on vire l'objet client associé
            # Supprimer cet objet permet de libérer le fichier traité précédemment : il redevient
            # accessible aux autres jurys... Pour qu'il reste verrouillé, il suffit de ne pas retourner
            # sur la page d'accueil !
            key = cherrypy.session['JE']
            self.clients.pop(key, '')
        cherrypy.session['JE'] = key # Stockée sur la machine client
        # Le client est-il sur la machine serveur ?
        if cherrypy.request.local.name == cherrypy.request.remote.ip:
            # Si oui, en mode TEST on affiche un menu de choix : "login Admin ou login Commission ?"
            # Si oui, en mode "normal", ce client est Admin
            if self.test: # Mode TEST ou pas ?
                # On affiche le menu qui propose un login Admin ou un login Commission
                return self.html_compose.menu()
            else:
                # Machine serveur et Mode normal ==> c'est un Client Admin
                # On créé un objet Admin associé à la clé key
                self.clients[key] = Admin(key)
        else:
            # Si non, c'est un Client Jury (peu importe qu'on soit en mode TEST)
            # On créé un objet Jury associé à la clé key
            self.clients[key] = Jury(key)
        # On affiche le menu du client
        return self.affiche_menu()
  
    @cherrypy.expose
    def affiche_menu(self):
        # lorsqu'appelée après appui sur le bouton 'RETOUR' proposé à l'admin,
        # on restitue des droits "vierges" de toute référence à une filière.
        client = self.get_client_cour()
        client.set_droits('') # on supprime la référence à une filière dans les droits (voir entête de page)
        if client.fichier: # le client a déjà sélectionné un fichier, mais il revient au menu
            self.fichiers_utilises.remove(client.fichier.nom) # on fait du ménage
            client.fichier = None
        # on redéfinit le type de retour (nécessaire quand on a utilisé des SSE)
        # voir la méthode 'refresh'.
        cherrypy.response.headers["content-type"] = "text/html"
        return self.html_compose.menu(client, self.fichiers_utilises, self.comm_en_cours)

    @cherrypy.expose
    def identification(self, **kwargs):
        # Admin ou Jury : fonction appelée par le formulaire de la page d'accueil EN MODE TEST UNIQUEMENT. 
        key = cherrypy.session['JE']
        if kwargs.get('acces', '') == "Accès administrateur":
            self.clients[key] = Admin(key) # création d'une instance admin
        else:
            self.clients[key] = Jury(key) # création d'une instance jury
        return self.affiche_menu() # Affichage du menu adéquat

    @cherrypy.expose
    def traiter_parcourssup(self, **kwargs):
        # Méthode appelée par l'Admin : bouton "TRAITER / VERIFIER"
        # Traite les données brutes de ParcoursSup : csv ET pdf
        cherrypy.response.headers["content-type"] = "text/event-stream"
        # trouver l'adjoint :
        def contenu():
            yield "Début du Traitement\n\n"
            ## Traitement des csv ##
            generateur = traiter_csv()
            for txt in generateur:
                yield txt
            ## Fin du traitement des csv ##
            ## Traitement des pdf ##
            #generateur = traiter_pdf()
            #for txt in generateur:
            #    yield txt
            # Fin du traitement pdf#
            # Faire des statistiques
            yield "\n     Décompte des candidatures\n\n"
            list_fich = [Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))]
            stat(list_fich)
            # Fin : retour au menu
            self.set_rafraich(True)
            yield "\n\nTRAITEMENT TERMINÉ.      --- VEUILLEZ CLIQUER SUR 'PAGE PRÉCÉDENTE' POUR REVENIR AU MENU  ---"
        return contenu()

    @cherrypy.expose
    def choix_comm(self, **kwargs):
        # Gère le choix fait dans le menu commission
        self.set_rafraich(True) # On rafraîchit les menus des Jurys...
        cherrypy.response.headers["content-type"] = "text/html"
        # récupère le client
        client = self.get_client_cour()
        # Teste si le fichier n'a pas été choisi par un autre jury
        if kwargs["fichier"] in self.fichiers_utilises:
            # Si oui, retour menu
            self.affiche_menu()
        else:
            # sinon, mise à jour des attributs du client
            client.set_fichier(Fichier(kwargs["fichier"]))
            # Mise à jour de la liste des fichiers utilisés
            self.fichiers_utilises.append(client.fichier.nom)
            ## Initialisation des paramètres
            # mem_scroll : cookie qui stocke la position de l'ascenseur dans la liste des dossiers
            cherrypy.session['mem_scroll'] = '0'
            # Affichage de la page de gestion des dossiers
            return self.affi_dossier()
    
    @cherrypy.expose
    def choix_admin(self, **kwargs):
        # Gère le choix fait dans le menu admin
        cherrypy.response.headers["content-type"] = "text/html"
        # récupère le client
        client = self.get_client_cour()
        # Mise à jour des attributs du client
        client.set_fichier(Fichier(kwargs["fichier"]))
        self.fichiers_utilises.append(client.fichier.nom)
        cherrypy.session['mem_scroll'] = '0'
        # Affichage de la page de gestion des dossiers
        return self.affi_dossier()      
    
    @cherrypy.expose
    def affi_dossier(self):
        # Fonction qui demande la génération de la page html contenant les dossiers
        # et qui la renvoie au navigateur qui la sollicite.
        # On transmets le client et le cookie de mémorisation de position d'ascenseur
        return self.html_compose.page_dossier(self.get_client_cour(), cherrypy.session['mem_scroll'])
    
    @cherrypy.expose
    def traiter(self, **kwargs):
        # Fonction appelée par l'appui sur "CLASSER" : valide les choix Jury ou Admin
        # Cette méthode est appelée par le bouton classer (ou NC) de la page dossier...
        # Elle sert à mettre à jour le dossier du candidat...
        # C'est le travail du client courant
        self.get_client_cour().traiter(**kwargs)    # chaque client traite à sa manière !!
        # Si Jury, on rafraîchit la page menu de l'admin (décompte des traitements)
        if isinstance(self.get_client_cour(), Jury):
            self.set_rafraich(True)
        # Et on retourne à la page dossier
        return self.affi_dossier()
        
    @cherrypy.expose
    def click_list(self, **kwargs):
        ## fonction appelée lors d'un click dans la liste de dossiers
        # Mémorisation de la position de l'ascenseur
        cherrypy.session["mem_scroll"] = kwargs['scroll_mem']
        # On récupère l'argument num
        txt = kwargs['num']
        # dont on extrait le numéro de dossier (3 premiers caractères)
        self.get_client_cour().num_doss = int(txt[:3])-1
        return self.affi_dossier()
    
    @cherrypy.expose
    def genere_fichiers_comm(self):
        # Générer les fichiers comm_XXXX.xml ou XXXX désigne une filière
        generation_comm()
        # Enfin, on retourne au menu
        return self.affiche_menu()

    @cherrypy.expose
    def clore_commission(self):
        clore_commission()
        # Et on retourne au menu
        return self.affiche_menu()
    
    @cherrypy.expose
    def page_impression(self, **kwargs):
        # Générer la page html pour impression des fiches bilan de commission
        # récupère le client
        client = self.get_client_cour()
        # Mise à jour des attributs du client
        client.set_fichier(Fichier(kwargs["fichier"]))
        self.fichiers_utilises.append(client.fichier.nom) ## A CHANGER, ON N'A PAS BESOIN DE ÇA SI ON PASSE {CLIENTS}
        return self.html_compose.page_impression(client)
    

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
cherrypy.quickstart(Serveur(test, ip),'/', config ="utils/config.conf")
