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


import os, sys, time, cherrypy, random, copy, glob, csv, pickle, webbrowser
from parse import parse
from lxml import etree
import utils.interface_xml as xml
import utils.decoupage_pdf as decoup
from utils.apb_csv import lire
from utils.nettoie_xml import nettoie
from utils.parametres import motivations
from utils.parametres import min_correc
from utils.parametres import max_correc
from utils.parametres import nb_correc
from utils.parametres import filieres
from utils.parametres import nb_jury


########################################################################
#                        Class Client                                  #
########################################################################

class Client(): # Objet client "abstrait" pour la class Serveur
    # Variables de classe :
    # Chargement de tous les "patrons" de pages HTML dans le dictionnaire "html" :
    with open(os.path. join(os.curdir, "utils", "patrons.html"), "r", encoding="utf8") as fi:
        html = {}
        for ligne in fi:
            if ligne.startswith("[*"):  # étiquette trouvée ==>
                label =ligne.strip()    # suppression LF et esp évent.
                label =label[2:-2]      # suppression [* et *]
                txt =""                 # début d'une page html
            else:
                if ligne.startswith("#####"):   # fin d'une page html
                    html[label] =txt            # on remplit le dictionnaire
                else:
                    txt += ligne
    
    # Fin variables de classe

    # constructeur
    def __init__(self, master, key, droits):
        self.je_suis = key  # identifiant du client : contenu du cookie déposé par le serveur sur la machine client
        self.master = master# l'instance serveur détenant ce client
        self.dossiers = []  # contenu du fichier xml traité par ce client
        self.num_doss = -1  # Cette valeur 'absurde' permet de détecter si le jury est en cours de traitement..
        self.fichier = ''   # nom du fichier traité par ce client
        self.droits = droits# admin ou jury...
        self.filiere = ''   # filière traitée (MPSI, PCSI, CPES, ..)
    
    # Accesseurs et mutateurs
    def get_je_suis(self):
        return self.je_suis

    def get_cand_cour(self):
        # retourne le candidat courant
        return self.dossiers[self.num_doss]
    
    def get_dossiers(self):
        return self.dossiers

    def get_master(self):
        return self.master

    def set_num_doss(self, num):
        self.num_doss = num
    
    def get_num_doss(self):
        return self.num_doss
    
    def set_fichier(self,fich):
        self.fichier = fich
    
    def get_fichier(self):
        return self.fichier
    
    def set_droits(self, droits):
        self.droits = droits
    
    def get_droits(self):
        return self.droits
    
    def set_filiere(self,fil):
        self.filiere = fil
    
    def get_filiere(self):
        return self.filiere
    # Fin accesseurs et mutateurs

    def mise_en_page_menu(self, header, contenu):
        # Fonction de "mise en page" des menus : renvoie une page HTML
        # avec un header et un contenu (liste d'actions) adéquats.
        data = {'header':header, 'contenu':contenu}
        return Client.html["MEP_MENU"].format(**data)
    
    def mise_en_page(self, visib, header, dossier='', liste=''):
        # Fonction de "mise en page" des dossiers : renvoie une page HTML
        # avec un header et un contenu (dossier, liste, script) adéquats.
        # visib sert à afficher (admin) ou non (jury) le bouton RETOUR.
        data = {'header':header,'dossier':dossier,'liste':liste,'visibilite':visib}
        return Client.html["miseEnPage"].format(**data)
    
    def lire_fichier(self):
        # Lit le fichier XML choisi et stocke son contenu dans l'attribut adéquat.
        parser = etree.XMLParser(remove_blank_text=True) # pour que pretty_print fonctionne
        self.dossiers = etree.parse(self.fichier, parser).getroot()

    def sauvegarder(self):
        # Méthode appelée par la méthode "traiter" du Serveur
        # Sauvegarde le fichier traité : mise à jour (par écrasement)
        # du fichier xml contenant les dossiers
        with open(self.fichier, 'wb') as fich:
            fich.write(etree.tostring(self.dossiers, pretty_print=True, encoding='utf-8'))
    
    def genere_header(self): 
        # Génère l'entête de page HTML
        # comme son nom l'indique, cette fonction génère une chaine
        # de caractères qui est le code html du header...
        sous_titre = ' - Accès {}.'.format(self.droits)
        return '<h1 align="center">EPA - Recrutement CPGE/CPES {}</h1>'.format(sous_titre)

########################################################################
#                        Class Jury                                    #
########################################################################

class Jury(Client): # Objet client (de type jury de commission) pour la class Serveur

    # constructeur : on créé une instance Client avec droits "jury" 
    def __init__(self, master, key):
        Client.__init__(self, master, key, 'Jury')

    # Accesseurs et mutateurs
    def set_droits(self, droits):
        Client.set_droits(self,'Jury '+droits)

    def get_liste_autres_fichiers_en_cours(self):
        # renvoie la liste des fichiers en cours de traitement.
        return self.master.get_autres_fichiers_en_cours(self)
    # Fin accesseurs et mutateurs

    def mise_en_page(self, header, dossier='', liste=''):
        # Fonction de "mise en page" des dossiers : renvoie une page HTML
        # avec un header et un contenu (dossier, liste, script) adéquats.
        return Client.mise_en_page(self, 'none', header, dossier, liste)
    
    def genere_menu(self):
        # Comme son nom l'indique..
        data = {}
        txt = self.genere_liste_comm()
        # On affiche le texte ci-dessous que s'il y a des fichiers à traiter.
        if txt != '':
            txt = '<h2>Veuillez sélectionner le fichier que vous souhaitez traiter.</h2>'+txt
        data['liste'] = txt
        return self.mise_en_page_menu(self.genere_header(), Client.html["menu_comm"].format(**data))

    def genere_liste_comm(self):
        # Compose le menu commission
        # On commence par chercher les fichiers destinés à la commission
        list_fich = glob.glob(os.path.join(os.curdir, "data", "epa_comm_*.xml"))
        txt = ''
        # on récupère la liste des fichiers traités par d'autres jurys
        list_fich_en_cours = self.get_liste_autres_fichiers_en_cours()
        # Chaque fichier apparaîtra sous la forme d'un bouton
        for fich in list_fich:
            txt += '<input type="submit" class = "fichier" name="fichier" value="{}"'.format(fich)
            fin = ''
            # Si un fichier est déjà traité par un autre jury, son bouton est disabled...
            if fich in list_fich_en_cours:
                fin = ' disabled'
            txt += fin
            txt += '/><br>'
        return txt
    
    def traiter(self, **kwargs):
        # Fonction lancée par la fonction "traiter" du Serveur. Elle même est lancée par validation d'un dossier
        # On récupère "l'objet" xml qui est une candidature
        cand  = self.dossiers[self.num_doss]
        ## On met à jour le contenu de ce dossier :
        # 1/ correction apportée par le jury et score final
        if kwargs['nc'] == 'NC':
            cor = 'NC'
            scoref = 'NC'
        else:
            cor = kwargs['correc']
            try:
                note = float(xml.get_scoreb(cand).replace(',','.'))
            except:
                note = 0
            note += float(cor)
            scoref = '{:.2f}'.format(note).replace('.',',')
        xml.set_correc(cand, cor)
        xml.set_scoref(cand, scoref)
        # 2/ Qui a traité le dossier
        xml.set_jury(cand,self.droits)
        # 2bis/ On met à jour le fichier des décomptes de commission
        if (xml.get_traite(cand) == '' and cor != 'NC'): # seulement si le candidat n'a pas déjà été vu et si validé!
            try:
                with open(os.path.join(os.curdir,"data","decomptes"), 'br') as fich:
                    decompt = pickle.load(fich)
                qui = self.get_droits()
                for key in decompt.keys():
                    if key in qui:
                        decompt[key] += 1
                with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') as stat_fich:
                    pickle.dump(decompt, stat_fich)
            except:
                none
        # 3/ "bouléen" traite : le dossier a été traité
        xml.set_traite(cand)
        # 4/ motivation du jury
        xml.set_motifs(cand, kwargs['motif'])
        ## Fin mise à jour dossier
        # Rafraichit la page menu (de l'admin)
        self.get_master().set_rafraich(True)
        # On sélectionne le dossier suivant
        if self.num_doss < len(self.dossiers)-1:
            self.num_doss = self.num_doss+1

########################################################################
#                        Class Admin                                   #
########################################################################

class Admin(Client): # Objet client (de type Administrateur) pour la class Serveur

    def __init__(self, master, key): 
        # constructeur : on créé une instance Client avec droits "admin"
        Client.__init__(self, master, key, 'Administrateur')
        self.autres_filieres = []       # contient la liste des autres (que celle traitée) filières
        self.fichiers_autres_fil = []   # contient les noms de fichiers des autres filières
        self.dossiers_autres_fil = []   # contenus des autres fichiers
        self.toutes_cand = []           # toutes les candidatures d'un candidat
    
    def set_droits(self, droits):
        Client.set_droits(self,'Administrateur' + droits)
    
    def mise_en_page(self, header, dossier='', liste=''):
        # Fonction de "mise en page" des dossiers : renvoie une page HTML
        # avec un header et un contenu (dossier, liste, script) adéquats.
        return Client.mise_en_page(self,'',header,dossier,liste)
    
    def genere_menu(self):
        # Compose le menu administrateur
        data = {}
        # Quel menu : avant commission ou après ??
        list_fich_comm = glob.glob(os.path.join(os.curdir,"data","epa_comm_*.xml"))
        if len(list_fich_comm) > 0: # après commission
            data['menu'] = 'apres'
            # Etape 4 bouton
            data['bout_etap4'] = '<input type = "button" class ="fichier"'
            data['bout_etap4'] += ' value = "Récolter les fichiers" onclick = "recolt_wait();"/>'
            data['decompt'] = self.genere_liste_decompte()
            data['liste_stat'] = self.genere_liste_stat()
            # Etape 5 bouton et Etape 6
            list_fich_class = glob.glob(os.path.join(os.curdir,"data","epa_class_*.xml"))
            txt5 = ''
            txt6 = ''
            if len(list_fich_class) > 0:
                txt5 = self.genere_liste_impression()
                txt6 = '<form id = "tableaux" action = "/tableaux_bilan" method = POST align = "center">'
                txt6 += '<input type = "button" class = "fichier" name = "tableaux"'
                txt6 += 'value = "Générer les tableaux bilan" onclick = "tableaux_wait();"/></form>'
                try:
                    if cherrypy.session['tableaux'] == 'ok':
                        txt6 += '<p>Ceux-ci sont disponibles dans le dossier "./tableaux"...</p>'
                except:
                    pass
            data['liste_impression'] = txt5
            data['form_tableaux'] = txt6
        
        else: # avant commission
            data['menu'] = 'avant'
            # liste csv
            data['liste_csv'] = self.genere_liste_csv()
            # liste pdf
            data['liste_pdf'] = self.genere_liste_pdf()
            # liste admin
            data['liste_admin'] = self.genere_liste_admin()
            # liste_stat
            data['liste_stat'] = self.genere_liste_stat()
            # Etape 3 bouton
            txt = ''
            if len(self.genere_liste_admin()) > 0:
                txt = '<input type = "button" class ="fichier" value = "Générer les fichiers commission"'
                txt += 'onclick = "genere_wait();"/>'
            data['bout_etap3'] = txt
        # Envoyez le menu
        txt = "menu_admin_{}".format(data['menu'])
        return self.mise_en_page_menu(self.genere_header(),Client.html[txt].format(**data))
    
    def genere_liste_csv(self):
        # Sous-fonction pour le menu admin
        txt = ''
        for fich in glob.glob(os.path.join(os.curdir,"data","*.csv")):
            txt += '{}<br>'.format(fich)
        return txt
    
    def genere_liste_pdf(self):
        # Sous-fonction pour le menu admin
        txt = ''
        for fich in glob.glob(os.path.join(os.curdir,"data","*.pdf")):
            txt += '{}<br>'.format(fich)
        return txt
    
    def genere_liste_admin(self):
        # Sous-fonction pour le menu admin
        list_fich = glob.glob(os.path.join(os.curdir,"data","epa_admin_*.xml"))
        txt = ''
        if len(list_fich) > 0:
            txt = '<h2>Choisissez le fichier que vous souhaitez compléter</h2>'
        for fich in list_fich:
            txt += '<input type="submit" class = "fichier" name="fichier" value="{}"/>'.format(fich)
            txt += '<br>'
        return txt
    
    def genere_liste_stat(self):
        # Sous-fonction pour le menu admin
        liste_stat = ''
        if len(glob.glob(os.path.join(os.curdir,"data","epa_admin_*.xml"))) > 0: # si les fichiers admin existent
            # lecture du fichier stat
            try:
                with open(os.path.join(os.curdir,"data","stat"), 'br') as fich:
                    stat = pickle.load(fich)
            except: # stat n'existe pas
                self.get_master().stat()
            with open(os.path.join(os.curdir,"data","stat"), 'br') as fich:
                stat = pickle.load(fich)
            # Création de la liste
            liste_stat = '<h4>Statistiques :</h4>'
            # Pour commencer les sommes par filières
            liste_stat += '<ul style = "margin-top:-5%">'
            deja_fait = [0] # sert au test ci-dessous si on n'a pas math.log2()
            for i in range(len(filieres)):
                liste_stat += '<li>{} dossiers {} validés</li>'.format(stat[2**i], filieres[i].upper())
                deja_fait.append(2**i)
            # Ensuite les requêtes croisées
            liste_stat += 'dont :<ul>'
            for i in range(2**len(filieres)):
                if not(i in deja_fait):  # avec la fonction math.log2 ce test est facile !!!
                    seq = []
                    bina = bin(i)[2:] # bin revoie une chaine qui commence par 'Ob' : on vire !
                    while len(bina) < len(filieres):
                        bina = '0{}'.format(bina) # les 0 de poids fort sont restaurés
                    for char in range(len(bina)):
                        if bina[char] == '1':
                            seq.append(filieres[len(filieres)-char-1].upper())
                    txt = ' + '.join(seq)
                    liste_stat += '<li>{} dossiers {}</li>'.format(stat[i], txt)
            liste_stat += '</ul></ul>'
        return liste_stat

    def genere_liste_decompte(self):
        # Sous-fonction pour le menu admin (pendant commission)
            try:
                with open(os.path.join(os.curdir,"data","decomptes"), 'br') as fich:
                    decompt = pickle.load(fich)
                    txt = ''
                for a in decompt.keys():
                    txt += '{} : {} dossiers classés<br>'.format(a, decompt[a])
            except:# aucun dossier n'a encore été traité...
                txt = ''
            return txt

    def genere_liste_impression(self):
        # Sous-fonction pour le menu admin
        list_fich = glob.glob(os.path.join(os.curdir,"data","epa_class_*.xml"))
        txt = ''
        if len(list_fich) > 0:
            txt = '<h2>Choisissez le fichier que vous souhaitez imprimer</h2>'
        for fich in list_fich:
            txt+= '<input type = "submit" class ="fichier" name = "fichier" value = "{}"/>'.format(fich)
            txt+='<br>'
        return txt
    
    def get_toutes_cand(self):
        # Trouver les autres filières demandées par le candidat courant
        self.autres_filieres = copy.deepcopy(filieres)
        self.autres_filieres.remove(self.filiere) # autres_filieres = filieres privée de filiere_courante
        # Identifiant du candidat courant
        iden = xml.get_id(self.dossiers[self.num_doss])
        r = parse('{}admin_{}.xml', self.fichier) # récupère le chemin vers les fichiers
        ## Récupération nom de fichier, dossiers, candidature
        self.fichiers_autres_fil = ['{}admin_{}.xml'.format(r[0],fil.upper()) for fil in self.autres_filieres]
        ## Dossiers
        parser = etree.XMLParser(remove_blank_text=True)
        # Ici, je rajoute un try: pour les cas où l'un des fichiers n'existerait pas (on n'est pas obligé)
        # de faire une commission avec toutes les filières à la fois...
        self.dossiers_autres_fil = []
        for fich in self.fichiers_autres_fil:
            try:
                self.dossiers_autres_fil.append(etree.parse(fich, parser).getroot())
            except:
                None
        # Candidatures
        self.toutes_cand = [self.dossiers[self.num_doss]] # 1ere candidature = candidature en cours..
        self.toutes_cand.extend([root.xpath('./candidat/id_apb[text()={}]'.format(iden))[0].getparent() for root in
        self.dossiers_autres_fil if root.xpath('./candidat/id_apb[text()={}]'.format(iden))])

    def traiter(self, **kwargs):
        # Traitement dossier avec droits administrateur
        # On récupère le dossier courant
        cand = self.dossiers[self.num_doss]
        # Ici, on va répercuter les complétions de l'administrateur dans tous les dossiers que le
        # candidat a déposé.
        # Recherche des autres candidatures : renvoie une liste (éventuellement vide) de candidature
        self.get_toutes_cand()

        ## Admin a-t-il changé qqc ? Si oui, mise à jour. 
            # Classe actuelle ?
        if xml.get_clas_actu(cand)!=kwargs['clas_actu']:
            for ca in self.toutes_cand: xml.set_clas_actu(ca,kwargs['clas_actu'])
            # semestres ?
        if kwargs.get('sem_prem','off')=='on': # kwargs ne contient 'sem_prem' que si la case est cochée !
            for ca in self.toutes_cand: xml.set_sem_prem(ca,'on')
        else:
            for ca in self.toutes_cand: xml.set_sem_prem(ca,'off')

        if kwargs.get('sem_term','off')=='on':
            for ca in self.toutes_cand: xml.set_sem_term(ca,'on')
        else:
            for ca in self.toutes_cand: xml.set_sem_term(ca,'off')
            # Cas des notes
        matiere = {'M':'Mathématiques','P':'Physique/Chimie'}
        date = {'1':'trimestre 1','2':'trimestre 2','3':'trimestre 3'}
        classe = {'P':'Première','T':'Terminale'}
        for cl in classe:
            for mat in matiere:
                for da in date:
                    key = cl + mat + da
                    if xml.get_note(cand,classe[cl],matiere[mat],date[da])!=kwargs[key]:
                        for ca in self.toutes_cand: xml.set_note(ca,classe[cl],matiere[mat],date[da],kwargs[key])
            # CPES
        if 'cpes' in xml.get_clas_actu(cand).lower():
            if xml.get_CM1(cand,True)!=kwargs['CM1']:
                for ca in self.toutes_cand: xml.set_CM1(ca, kwargs['CM1'])
            if xml.get_CP1(cand,True)!=kwargs['CP1']:
                for ca in self.toutes_cand: xml.set_CP1(ca, kwargs['CP1'])
            # EAF écrit et oral...      
        if xml.get_ecrit_EAF(cand)!=kwargs['EAF_e']:
            for ca in self.toutes_cand: xml.set_ecrit_EAF(ca, kwargs['EAF_e'])
        if xml.get_oral_EAF(cand)!=kwargs['EAF_o']:
            for ca in self.toutes_cand: xml.set_oral_EAF(ca, kwargs['EAF_o'])
        # On (re)calcule le score brut !
        xml.calcul_scoreb(cand)
        xml.is_complet(cand) # mise à jour de l'état "dossier complet"
        # Commentaire éventuel admin
        motif = kwargs['motif']
        if not('- Admin :' in motif or motif==''):
            motif = '- Admin : {}'.format(motif)
        for ca in self.toutes_cand: xml.set_motifs(ca, motif)
        # L'admin a validé le formulaire avec le bouton NC (le candidat ne passera pas en commission)
        if kwargs['nc'] == 'NC':
            xml.set_correc(cand, 'NC') # la fonction calcul_scoreb renverra 0 !
        else:
            xml.set_correc(cand, '0')

        # Sauvegarde autres candidatures
        for i in range(len(self.dossiers_autres_fil)):
            with open(self.fichiers_autres_fil[i], 'wb') as fich:
                fich.write(etree.tostring(self.dossiers_autres_fil[i], pretty_print=True, encoding='utf-8'))
    
    def lire_fichier(self): # Comment on dit déjà : écrire par dessus la méthode de la classe mère...
        # Lit le fichier XML choisi et vérifie la complétude des dossiers
        Client.lire_fichier(self)
        for cand in self.dossiers:
            xml.is_complet(cand) # on renseigne le noeud complet (oui/non)

########################################################################
#                        Class Serveur                                 #
########################################################################

class Serveur(): # Objet lancé par cherrypy dans le __main__
    "Classe générant les objets gestionnaires de requêtes HTTP"
    
    # Attributs de classe
    # corrections proposées aux jurys (faire attention que 0 soit dans la liste !!)
    corrections = [(n+min_correc*nb_correc)/float(nb_correc) for n in range(0,(max_correc-min_correc)*nb_correc+1)]
    # Fin déclaration attributs de classe

    def __init__(self, test, ip):
        # constructeur
        self.clients =  {}# dictionnaire contenant les clients connectés
        self.test = test # booléen : exécution de la version test (avec, notamment, un menu "Admin or Jury ?")
        self.rafraich = False # booléen qui sert à activer ou nom la fonction refresh
        navi = webbrowser.get() # Quel est le navigateur par défaut ?
        navi.open_new('http://'+ip+':8080') # on ouvre le navigateur internet, avec la bonne url..

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
            yield "retry: 500\n\n"
            if self.get_rafraich():
                self.set_rafraich(False) # On ne rafraîchit qu'une fois à la fois !
                yield "event: message\ndata: ok\n\n"
        return msg()

    # Accesseurs et mutateurs
    def get_client_cour(self):
        return self.clients[cherrypy.session["JE"]]

    def get_cand_cour(self):
        return self.get_client_cour().get_cand_cour()

    def get_autres_fichiers_en_cours(self, client):
        lis = []
        autres_clients = [cli for cli in self.clients if self.clients[cli]!=client]
        for cli in autres_clients:
            if self.clients[cli].get_num_doss() != -1:
                lis.append(self.clients[cli].get_fichier())
        return lis
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
                data = {'header':self.genere_header(), 'contenu':Client.html["pageAccueil"].format('')}
                return Client.html["MEP_MENU"].format(**data)
            else:
                # Machine serveur et Mode normal ==> c'est un Client Admin
                # On créé un objet Admin associé à la clé key
                self.clients[key] = Admin(self, key)
        else:
            # Si non, c'est un Client Jury (peu importe qu'on soit en mode TEST)
            # On créé un objet Jury associé à la clé key
            self.clients[key] = Jury(self, key)
        # On affiche le menu du client
        return self.clients[key].genere_menu()
  
    @cherrypy.expose
    def identification(self, **kwargs):
        # Admin ou Jury : fonction appelée par le formulaire de la page d'accueil EN MODE TEST UNIQUEMENT. 
        key = cherrypy.session['JE']
        if kwargs['acces'] == "Accès administrateur":
            self.clients[key] = Admin(self,key) # création d'une instance admin
        else:
            self.clients[key] = Jury(self,key) # création d'une instance jury
        return self.clients[key].genere_menu() # Affichage du menu adéquat

    @cherrypy.expose
    def retour_menu(self):
        # Retour menu : sert essentiellement à l'Admin ; bouton RETOUR de la page dossier
        self.get_client_cour().set_droits('')
        cherrypy.response.headers["content-type"] = "text/html"
        return self.get_client_cour().genere_menu()
    
    def efface_dest(self, chem):
        # Sert dans traiter_csv et dans tableaux/bilans
        # Supprime les dossiers pointés par le chemin chem
        for filename in os.listdir(chem):
            fich = os.path.join(chem, filename)
            try:
                os.remove(fich)
            except: # cas d'un sous-dossier
                self.efface_dest(fich) # appel récursif pour vider le contenu du sous-dossier
                os.rmdir(fich) # suppression du sous-dossier

    def trouve(self, iden, num_fil, cc, root, fil):
        # Sous-fonction de la fonction stat...
        # Sert à construire le binaire '001', '101', etc, indiquant les candidatures multiples..
        if num_fil < len(root)-1:  
            cand = root[num_fil+1].xpath('./candidat/id_apb[text()={}]'.format(iden))
            if cand:
                cc |= 2**(filieres.index(fil[num_fil + 1].lower())) # un OU évite les surcomptes !
            cc = self.trouve(iden, num_fil + 1, cc, root, fil)
            if cand: xml.set_candidatures(cand[0].getparent(), cc)
        return cc
            
    def stat(self):
        # Effectue des statistiques sur les candidats
        list_fich = glob.glob(os.path.join(os.curdir, "data", "epa_admin_*.xml"))
        parser = etree.XMLParser(remove_blank_text=True)
        root = [etree.parse(fich, parser).getroot() for fich in list_fich]
        fil = [parse(os.path.join(os.curdir, "data", "epa_admin_{}.xml"), fich)[0] for fich in list_fich]

        # Initialisation des compteurs
        # L'info de candidatures est stockée dans un nombre binaire ou 1 bit 
        # correspond à 1 filière. Un dictionnaire 'candid' admet ces nombres binaires pour clés,
        # et les valeurs sont des nombres de candidats. 
        # candid = {'001' : 609, '011' : 245, ...} indique que 609 candidats ont demandé
        # le filière 1 et 245 ont demandé à la fois la filière 1 et la filière 2

        # Initialisation du dictionnaire stockant toutes les candidatures
        candid = {}
        for i in range(2**len(filieres)):
            candid[i] = 0
    
        # Recherche des candidatures
        # On stocke dans une liste les identifiants des candidats vus,
        # cela évite de les trouver 2 fois...
        deja_vu = []
        for i in range(len(root)):  # i, indice de filière
            for candi in root[i]:   # pour toutes les candidatures de la filière i
                index = filieres.index(fil[i].lower()) # trouver le compteur adéquat
                if xml.get_motifs(candi) != '- Admin : Candidature non validée sur ParcoursSUP':
                    candid[2**index] += 1 # Un candidat de plus dans cette filière
                iden = xml.get_id(candi)
                # puis recherche du même candidat dans les autres filières,
                # création du nombre stockant les filières demandées
                # et incrémentation du compteur adéquat
                if not(iden in deja_vu): # candidat pas encore vu
                    deja_vu.append(iden)
                    cc = 2**index # le bit 'index' du candidat est ON
                    cc = self.trouve(iden, i, cc, root, fil)
                    xml.set_candidatures(candi, cc) # on écrit le binaire obtenu dans le dossier candidat
                    # Incrémentation des compteurs
                    for j in range(2**len(filieres)):
                        if (cc == j and cc != 2**index and xml.get_motifs(candi) !=
                                '- Admin : Candidature non validée sur ParcoursSUP'): #  seulement les multi-candidatures
                            candid[j] += 1
        # Sauvegarder
        for i in range(len(root)):
            with open(list_fich[i], 'wb') as fi:
                fi.write(etree.tostring(root[i], pretty_print=True, encoding='utf-8'))
        
        # Écrire le fichier stat
        with open(os.path.join(os.curdir, "data", "stat"), 'wb') as stat_fich:
            pickle.dump(candid, stat_fich)
            
    @cherrypy.expose
    def traiter_apb(self, **kwargs):
        # Méthode appelée par l'Admin : bouton "TRAITER / VERIFIER"
        # Traite les données brutes d'APB : csv ET pdf
        cherrypy.response.headers["content-type"] = "text/event-stream"
        def contenu():
            yield "Début du Traitement\n\n"
            ## Traitement des csv ##
            yield "     Début du traitement des fichiers csv\n"
            for source in glob.glob(os.path.join(os.curdir, "data", "*.csv")):
                for fil in filieres:
                    if fil in source.lower(): # Attention le fichier csv doit contenir la filière...
                        dest = os.path.join(os.curdir, "data", "epa_admin_{}.xml".format(fil.upper()))
                        yield "         Fichier {} ... ".format(parse("{}epa_admin_{}.xml", dest)[1])
                        xml = lire(source)  # fonction contenue dans apb_csv.py
                        xml = nettoie(xml) # Petite toilette du résultat de apb_csv...
                        with open(dest, 'wb') as fich:
                            fich.write(etree.tostring(xml, pretty_print=True, encoding='utf-8'))
                        yield "traité.\n"
            ## Fin du traitement des csv ##
            ## Traitement des pdf ##
            yield "\n     Début du traitement des fichiers pdf (traitement long, restez patient...)\n"
            dest = os.path.join(os.curdir, "data", "docs_candidats")
            try:
                self.efface_dest(dest) # on efface toute l'arborescence fille de dest
            except: # dest n'existe pas !
                os.mkdir(dest) # on le créé...
            for fich in glob.glob(os.path.join(os.curdir, "data", "*.pdf")):
                for fil in filieres:
                    if fil in fich.lower():
                        yield "         Fichier {} ... ".format(fil.upper())
                        desti = os.path.join(dest,fil)
                        os.mkdir(desti)
                        decoup.decoup(fich, desti) # fonction contenue dans decoupage_pdf.py
                        yield "traité.\n".format(parse("{}_{4s}.pdf", fich)[1])
            # Fin du traitement pdf#
            # Faire des statistiques
            yield "\n     Décompte des candidatures\n\n"
            self.stat()
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
        # Ce test est nécessaire parce que le "disabled" des boutons correspondants n'est
        # pas effectif si les jurys se connectent "en même temps"... Pour que le "disabled"
        # prenne effet, il faudrait recharger la page.
        if kwargs["fichier"] in self.get_autres_fichiers_en_cours(client):
            # Si oui, retour menu
            self.retour_menu()
        else:
            # sinon
            # Mise à jour des attributs du client
            client.set_fichier(kwargs["fichier"])
            r = parse('{}comm_{}{:d}.xml', kwargs["fichier"]) # récupère nom du jury
            client.set_droits(r[1] + str(r[2])) # les droits (qui servent dans le titre) sont complétés
            client.set_filiere(r[1].lower())
            # Ici, on va charger les dossiers présents dans le fichier choisi :
            client.lire_fichier()
            # Initialisation des paramètres
            client.set_num_doss(0) # on commence par le premier !
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
        client.set_fichier(kwargs["fichier"])
        r = parse('{}admin_{}.xml', kwargs["fichier"]) # récupère nom de la filière traitée
        client.set_droits(' {}'.format(r[1]))
        client.set_filiere(r[1].lower())
        # Ici, on va charger les dossiers présents dans le fichier choisi :
        client.lire_fichier()
        # Initialisation des paramètres
        client.set_num_doss(0) # on commence par le premier !
        cherrypy.session['mem_scroll'] = '0'
        # Affichage de la page de gestion des dossiers
        return self.affi_dossier()      
    
    @cherrypy.expose
    def affi_dossier(self):
        # Fonction qui génère la page html contenant les dossiers
        # Renvoie une page HTML, formatée avec le nom de la commission :
        # Quel client ?
        client = self.get_client_cour()
        # Quels droits ?
        droits = self.get_client_cour().get_droits()
        # Quel candidat ?
        cand = self.get_cand_cour()
        # On génère les 3 parties de la page html
        self.header = client.genere_header()
        self.dossier = self.genere_dossier(cand, droits)
        self.liste = self.genere_liste()
        # On retourne cette page au navigateur
        return client.mise_en_page(self.header, self.dossier, self.liste)
    
    @cherrypy.expose
    def traiter(self, **kwargs):
        # Fonction appelée par l'appui sur "VALIDER" : valide les choix Jury ou Admin
        # Cette méthode est appelée par le bouton valider de la page dossier...
        # **kwargs empaquette les arguments passés par le navigateur dans le dictionnaire kwargs..
        # mise à jour dans les variables de session du dossier du candidat...
        client = self.get_client_cour()
        client.traiter(**kwargs)    # chaque client traite à sa manière !!
        ## Et on sauvegarde immédiatement tout cela...
        client.sauvegarder()
        # Et on retourne au traitement...
        cherrypy.response.headers["content-type"] = "text/html"
        return self.affi_dossier()
        
    @cherrypy.expose
    def click_list(self, **kwargs):
        ## fonction appelée lors d'un click dans la liste de dossiers
        cherrypy.session["mem_scroll"] = kwargs['scroll_mem']
        txt = kwargs['num'] # on récupère l'argument num
        num_doss = int(txt[:3])-1 # on en extrait le numéro de dossier  (3 premiers caractères)
        self.get_client_cour().set_num_doss(num_doss) # le client change de num_doss
        return self.affi_dossier()
    
    def genere_dict(self, cand, droits):
        # Renvoie le dictionnaire contenant les infos du dossier en cours
        # On passe droits en argument car la fonction qui imprime les fiches bilan de commission
        # est lancée par Admin, mais l'impression se fait avec un dossier formaté comme pour
        # Jury : les notes de sont pas des <input type="text" .../>
        data = {'Nom':xml.get_nom(cand) + ', ' + xml.get_prenom(cand)}
        data['naiss'] = xml.get_naiss(cand)
        data['etab'] = xml.get_etab(cand)
        txt = '[{}]-{}'.format(xml.get_id(cand), xml.get_INE(cand))
        data['id'] = txt
        # récup filiere
        fil = self.get_client_cour().get_filiere()
        data['ref_fich'] = os.path.join('docs_candidats', '{}'.format(fil), 'docs_{}'.format(xml.get_id(cand)))
        if 'admin' in droits.lower():
            clas_inp = '<input type="text" id="clas_actu" name = "clas_actu" size = "10"\
            value="{}"/>'.format(xml.get_clas_actu(cand))
            data['clas_actu'] = clas_inp
        else:
            data['clas_actu'] = xml.get_clas_actu(cand)
        # Cases à cocher semestres : actives pour l'Admin, inactives sinon
        visib = 'disabled '
        if 'admin' in droits.lower():
            visib = ' '
        txt = visib
        if xml.get_sem_prem(cand) == 'on': txt += 'checked'
        data['sem_prem'] = txt
        txt = visib
        if xml.get_sem_term(cand) == 'on': txt += 'checked'
        data['sem_term'] = txt
        # Notes
        matiere = {'M':'Mathématiques', 'P':'Physique/Chimie'}
        date = {'1':'trimestre 1', '2':'trimestre 2', '3':'trimestre 3'}
        classe = {'P':'Première', 'T':'Terminale'}
        for cl in classe:
            for mat in matiere:
                for da in date:
                    key = cl + mat + da
                    note = '{}'.format(xml.get_note(cand, classe[cl], matiere[mat], date[da]))
                    note_inp = '<input type = "text" class = "notes grossi" id = "{}" name = "{}" value = "{}"\
                    onfocusout = "verif_saisie()"/>'.format(key, key, note)
                    if 'admin' in droits.lower():
                        data[key] = note_inp
                    else:
                        data[key] = note
        # CPES
        cpes = False
        if 'cpes' in xml.get_clas_actu(cand).lower():
            cpes = True
        if 'admin' in droits.lower():
            note_CM1 = '<input type = "text" class = "notes grossi" id = "CM1" name = "CM1" value = "{}" onfocusout =\
            "verif_saisie()"/>'.format(xml.get_CM1(cand, cpes))
            data['CM1'] = note_CM1
            note_CP1 = '<input type = "text" class = "notes grossi" id = "CP1" name = "CP1" value = "{}" onfocusout =\
            "verif_saisie()"/>'.format(xml.get_CP1(cand, cpes))
            data['CP1'] = note_CP1
        else:
            data['CM1'] = '{}'.format(xml.get_CM1(cand, cpes))
            data['CP1'] = '{}'.format(xml.get_CP1(cand, cpes))
        # EAF
        if 'admin' in droits.lower():
            note_eaf_e = '<input type = "text" class = "notes grossi" id = "EAF_e" name = "EAF_e" value = "{}"\
            onfocusout = "verif_saisie()"/>'.format(xml.get_ecrit_EAF(cand))
            data['EAF_e'] = note_eaf_e
            note_eaf_o = '<input type = "text" class = "notes grossi" id = "EAF_o" name = "EAF_o" value = "{}"\
            onfocusout = "verif_saisie()"/>'.format(xml.get_oral_EAF(cand))
            data['EAF_o'] = note_eaf_o
        else:
            data['EAF_e'] = xml.get_ecrit_EAF(cand)
            data['EAF_o'] = xml.get_oral_EAF(cand)      
        # Suite
        data['scoreb'] = xml.get_scoreb(cand)
        data['scoref'] = xml.get_scoref(cand)
        data['cand'] = xml.get_candidatures(cand, 'impr')
        return data
    
    def genere_header(self): 
        # Génère l'entête de page HTML
        # comme son nom l'indique, cette fonction génère une chaine de caractères qui est le code html du header...
        qqn = self.clients.get(cherrypy.session['JE'], False)
        sous_titre = ''
        if qqn: # sur la page d'accueil, pas de sous-titre...
            sous_titre = ' - Accès {}.'.format(qqn.get_droits())
        return '<h1 align="center">EPA - Recrutement CPGE/CPES {}</h1>'.format(sous_titre)
    
    def genere_dossier(self, cand, droits):
        # Génère la partie dossier de la page HTML
        # récupération correction
        correc = str(xml.get_correc(cand))
        ncval = ''
        if correc == 'NC':
            correc = 0
            ncval = 'NC'
        # Construction de la barre de correction :
        barre = '<tr><td width = "2.5%"></td><td>'
        barre += '<input type = "range" class = "range" min="-3" max = "3" step = ".25" name = "correc" id = "correc"\
        onchange="javascript:maj_note();" onmousemove="javascript:maj_note();" onclick="click_range();" value =\
        "{}"/>'.format(correc)
        barre += '</td><td width = "2.5%"></td></tr>' # fin de la ligne range
        txt = '' # on construit maintenant la liste des valeurs...
        for i in range(0, len(Serveur.corrections) + 1):
            if (i % 2 == 0):
                txt += '<td width = "7%">{:+3.1f}</td>'.format(Serveur.corrections[i])
        barre += '<tr><td align = "center" colspan = "3"><table width = "100%"><tr class =\
        "correc_notimpr">{}</tr></table>'.format(txt)
        barre += '<span class = "correc_impr">'+xml.get_jury(cand)+' : {:+.2f}'.format(float(correc))+'</span>'
        barre += '</td></tr>'
        # input hidden nc
        nc = '<input type="hidden" id = "nc" name = "nc" value = "{}"/>'.format(ncval)
        # Construction de la chaine motifs.
        motifs = ''
        # le premier motif : champ texte.
        motifs += '<tr><td align = "left">'
        motifs += '<input type="text" class = "txt_motifs" name="motif" id = "motif" value= "'
        try:
            txt = xml.get_motifs(cand)
        except :
            txt = ''
        motifs += '{}"/></td></tr>'.format(txt)
        # La suite : motifs pré-définis
        for i in range(0, len(motivations)):
            key = 'mot_' + str(i)
            motifs += '<tr><td align = "left"><input type="button" name="'+key
            motifs += '" id="'+key+'" onclick="javascript:maj_motif(this.id)"'
            motifs += ' class = "motif" value ="'+ motivations[i]+'"/></td></tr>'
    
        # On met tout ça dans un dico data pour passage en argument à page_dossier
        data = self.genere_dict(cand, droits)
        data['barre'] = barre
        data['nc'] = nc
        data['motifs'] = motifs
        return Client.html["page_dossier"].format(**data)
        
    def genere_liste(self):
        # Génère la partie liste de la page HTML
        client = self.get_client_cour()
        liste = client.get_dossiers()
        num_doss = client.get_num_doss()
        # Construction de la chaine lis : code html de la liste des dossiers.
        lis = '<form id = "form_liste" action = "click_list" method=POST>'
        lis += '<input type="hidden" name = "scroll_mem" value = "'
        lis += cherrypy.session['mem_scroll']+'"/>' # mémo du scroll
        for i in range(0, len(liste)):
            lis += '<input type = "submit" name="num" '
            clas = 'doss'
            if i == num_doss: # affecte la class css "doss_courant" au dossier courant
                    clas += ' doss_courant'
            if xml.get_traite(liste[i]) != '':
                    clas += ' doss_traite' # affecte la classe css "doss_traite" aux ...
            if 'admin' in client.get_droits().lower():
                if xml.get_correc(liste[i]) == 'NC':
                    clas += ' doss_rejete'
                else: 
                    if xml.get_complet(liste[i]) == 'non':  # Dossier incomplet (seulement admin ?)
                        clas += ' doss_incomplet'
            lis += 'class = "{}"'.format(clas)
            nom = xml.get_nom(liste[i])+', '+xml.get_prenom(liste[i])
            txt = '{:3d}) {: <30}{}'.format(i+1, nom[:29], xml.get_candidatures(liste[i]))
            lis += ' value="'+txt+'"></input><br>'
        # txt est le txt que contient le bouton. Attention, ses 3 premiers
        # caractères doivent être le numéro du dossier dans la liste des
        # dossiers (client_get_dossiers())... Cela sert dans click_list(), pour identifier sur qui on a clické..
        lis += '-'*7 + ' fin de liste ' + '-'*7
        lis = lis + '</form>'
        return lis
    
    @cherrypy.expose
    def genere_fichiers_comm(self):
        # Générer les fichier epa_comm_mpsi1.xml jusqu'à epa_comm_cpesN.xml
        # Récupération des fichiers admin
        list_fich = glob.glob(os.path.join(os.curdir, "data", "epa_admin_*.xml"))
        # Pour chaque fichier "epa_admin_*.xml"
        for fich in list_fich:
            parser = etree.XMLParser(remove_blank_text=True)
            doss = etree.parse(fich, parser).getroot()
            # Tout d'abord, calculer le score brut de chaque candidat 
            for cand in doss:
                xml.calcul_scoreb(cand)
            # Classement par scoreb décroissant et renseignement du noeud "rang brut"
            doss[:] = sorted(doss, key = lambda cand: -float(cand.xpath('diagnostic/score')[0].text.replace(',','.')))
            rg = 1
            num = 1
            score_actu = xml.get_scoreb(doss[0])
            for cand in doss:
                if xml.get_scoreb(cand) < score_actu:
                    score_actu = xml.get_scoreb(cand)
                    rg = num
                xml.set_rang_brut(cand, str(rg))
                num += 1
            # Récupération de la filière 
            fil = parse(os.path.join(os.curdir, "data", "epa_admin_{}.xml"), fich)
            nbjury = int(nb_jury[fil[0].lower()])
            # Découpage en n listes de dossiers
            for j in range(0, nbjury):
                dossier = []    # deepcopy ligne suivante sinon les candidats sont retirés de doss à chaque append
                [dossier.append(copy.deepcopy(doss[i])) for i in range(0, len(doss)) if i%nbjury == j]
                # Sauvegarde
                res = etree.Element('candidats')
                [res.append(cand) for cand in dossier]
                nom = os.path.join(os.curdir, "data", "epa_comm_{}{}.xml".format(fil[0], j+1))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
        # Création fichier decompte
        decompt = {}
        for fil in filieres:
            decompt['{}'.format(fil.upper())]=0
        with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') as stat_fich:
            pickle.dump(decompt, stat_fich)
        # Enfin, on retourne au menu
        return self.retour_menu()

    def convert(self, naiss):
        # Convertit une date de naissance en un nombre pour le classement
        dic = parse('{j:d}/{m:d}/{a:d}', naiss)
        return dic['a']*10**4 + dic['m']*10**2 + dic['j']
    
    @cherrypy.expose
    def genere_fichiers_class(self):
        # Récolter les fichiers après la commission
        # Pour chaque filière
        tot_class = {} # dictionnaire contenant les nombres de candidats classés par filière
        for comm in filieres:
            list_fich = glob.glob(os.path.join(os.curdir, "data", "epa_comm_{}*.xml".format(comm.upper())))
            list_doss = [] # contiendra les dossiers de chaque sous-comm
            # Pour chaque sous-commission
            for fich in list_fich:
                # lecture fichier
                parser = etree.XMLParser(remove_blank_text=True)
                doss = etree.parse(fich, parser).getroot()
                # Les fichiers non vus se voient devenir NC avec
                # motifs = "Dossier moins bon que le dernier classé" (sauf si admin a renseigné un motif)
                for c in doss:
                    if xml.get_jury(c) == 'Auto':
                        xml.set_correc(c, 'NC')
                        xml.set_scoref(c, 'NC')
                        if xml.get_motifs(c) == '':
                            xml.set_motifs(c, 'Dossier moins bon que le dernier classé.')
                # Classement selon score_final + age
                doss[:] = sorted(doss, key = lambda cand: self.convert(cand.xpath('naissance')[0].text))
                doss[:] = sorted(doss, key = lambda cand: -float(xml.get_scoref_num(cand).replace(',','.')))
                # On ajoute dans list_doss
                list_doss.append(doss)
            # Ensuite, on entremêle les dossiers de chaque sous-comm
            doss_fin = []
            if list_doss: # Y a-t-il des dossiers dans cette liste ?
                nb = len(list_doss[0])
                num = 0
                for i in range(0, nb): # list_doss[0] est le plus grand !!
                    doss_fin.append(list_doss[0][i])
                    for k in range(1, len(list_doss)): # reste-t-il des candidats classés dans les listes suivantes ?
                        if i < len(list_doss[k]): doss_fin.append(list_doss[k][i])
                res = etree.Element('candidats')
                [res.append(c) for c in doss_fin]
                # Rang
                rg = 1
                for cand in res:
                    nu = 'NC'
                    if xml.get_scoref(cand) != 'NC':
                        nu = str(rg)
                        rg += 1
                    xml.set_rang_final(cand, nu)
                # Sauvegarde du fichier class...
                nom = os.path.join(os.curdir, "data", "epa_class_{}.xml".format(comm.upper()))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
            tot_class.update({"{}".format(comm.upper()):rg-1})
        # On écrit le fichier des décomptes de commission
        with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') as stat_fich:
            pickle.dump(tot_class, stat_fich)
        # Enfin, on retourne au menu
        return self.retour_menu()
    
    @cherrypy.expose
    def page_impression(self, **kwargs):
        # Générer la page html pour impression des fiches bilan de commission
        r = parse('{}class_{}.xml', kwargs["fichier"]) # récupère nom commission
        txt = ''
        saut = '<div style = "page-break-after: always;"></div>'
        parser = etree.XMLParser(remove_blank_text=True)
        for cand in etree.parse(kwargs["fichier"], parser).getroot():
            if xml.get_scoref(cand) != 'NC':
                txt += '<h1 align="center" class = "titre">EPA - Recrutement CPGE/CPES - {}</h1>'.format(r[1].upper())
                # Le test suivant est un résidu d'une époque où on générait une fiche même si le candidat n'était pas 
                # classé !
                if xml.get_rang_final(cand) == 'NC':
                    txt += '<div class = encadre>Candidat non classé</div>'
                else:
                     txt += '<div class = encadre>Candidat classé : {}</div>'.format(xml.get_rang_final(cand))
                txt += self.genere_dossier(cand, "commission")
                txt += saut
        txt = txt[:-len(saut)] # On enlève le dernier saut de page...
        data = {'pages':txt}
        return Client.html['page_impress'].format(**data) 
    
    # Générer les tableaux .csv bilans de la commission
    @cherrypy.expose
    def tableaux_bilan(self):
        # Un peu de ménage...
        dest = os.path.join(os.curdir, "tableaux")
        try:
            self.efface_dest(dest) # on efface toute l'arborescence fille de dest
        except: # dest n'existe pas !
            os.mkdir(dest) # on le créé...
        # Création du fichier d'aide
        with open(os.path.join(dest, "aide.txt"), 'w') as fi:
            txt = ("En cas de difficultés à ouvrir les .csv avec EXCEL,\n"
            "il est conseillé d'utiliser le menu fichier-->importer")
            fi.write(txt)
        fi.close()
        # Récupération des fichiers
        list_fich = glob.glob(os.path.join(os.curdir, "data", "epa_class_*.xml"))
        # Pour chaque filière :
        for fich in list_fich:
            # lecture fichier
            parser = etree.XMLParser(remove_blank_text=True)
            doss = etree.parse(fich, parser).getroot()
            # 1er tableau : liste ordonnée des candidats retenus, pour l'admin
            nom = os.path.join(os.curdir, "tableaux", "") # chaîne vide pour avoir / à la fin du chemin...
            nom += parse(os.path.join(os.curdir, "data", "epa_class_{}.xml"), fich)[0]
            nom += '_retenus.csv'
            c = csv.writer(open(nom, 'w'))
            entetes = ['Rang brut', 'Rang final', 'Nom', 'Prénom', 'Date de naissance', 'score brut', 'correction', 
            'score final', 'jury', 'Observations']
            c.writerow(entetes)
            for cand in doss:
                if xml.get_scoref(cand) != 'NC': # seulement les classés !!
                    data = [fonction(cand) for fonction in [xml.get_rang_brut, xml.get_rang_final, xml.get_nom, 
                    xml.get_prenom, xml.get_naiss, xml.get_scoreb, xml.get_correc, xml.get_scoref, xml.get_jury, 
                    xml.get_motifs]]
                    c.writerow(data)
            # 2e tableau : liste ordonnée des candidats retenus, pour Bureau des élèves
            # Le même que pour l'admin, mais sans les notes, ni les rangs bruts...
            nom = os.path.join(os.curdir, "tableaux", "") # chaîne vide pour avoir / à la fin du chemin..
            nom += parse(os.path.join(os.curdir, "data", "epa_class_{}.xml"), fich)[0]
            nom += '_retenus(sans_note).csv'
            c = csv.writer(open(nom, 'w'))
            entetes = ['Rang final', 'Nom', 'Prénom', 'Date de naissance']
            c.writerow(entetes)
            for cand in doss:
                if xml.get_scoref(cand) != 'NC': # seulement les classés !!
                    data = [fonction(cand) for fonction in [xml.get_rang_final , xml.get_nom, 
                    xml.get_prenom, xml.get_naiss]]
                    c.writerow(data)
            # 3e tableau : Liste alphabétique de tous les candidats avec le numéro dans le classement,
            # toutes les notes et qq infos administratives
            # Fichier destination
            nom = os.path.join(os.curdir, "tableaux", "") # chaîne vide pour avoir / à la fin du chemin...
            nom += parse(os.path.join(os.curdir, "data", "epa_class_{}.xml"), fich)[0]
            nom += '_alphabetique.csv'
            c = csv.writer(open(nom, 'w'))
            entetes = ['Rang brut', 'Rang final', 'Candidatures', 'Nom', 'Prénom', 'Date de naissance', 'Sexe', 
            'Nationalité', 'id_apb', 'Boursier', 'Classe actuelle', 'Etablissement', 'Commune Etablissement']
            # entêtes notes...
            matiere = {'M':'Mathématiques', 'P':'Physique/Chimie'}
            date = {'1':'trimestre 1', '2':'trimestre 2', '3':'trimestre 3'}
            classe = {'P':'Première', 'T':'Terminale'}
            entetes.extend([cl + mat + da for cl in classe for da in date for mat in matiere])
            entetes.extend(['F_écrit', 'F_oral', 'CPES_math', 'CPES_phys'])
            # la suite
            entetes.extend(['score brut', 'correction', 'score final', 'jury', 'Observations'])
            c.writerow(entetes)
            # Classement alphabétique
            doss[:] = sorted(doss, key = lambda cand: xml.get_nom(cand))
            # Remplissage du fichier dest
            for cand in doss:
                data = [xml.get_rang_brut(cand), xml.get_rang_final(cand), xml.get_candidatures(cand)]
                data += [fonction(cand) for fonction in [xml.get_nom, xml.get_prenom, xml.get_naiss, xml.get_sexe,
                xml.get_nation, xml.get_id, xml.get_boursier, xml.get_clas_actu, xml.get_etab, xml.get_commune_etab]]
                # Les notes...
                for cl in classe:
                    for da in date:
                        for mat in matiere:
                            key = cl + mat + da
                            note = '{}'.format(xml.get_note(cand, classe[cl], matiere[mat],date[da]))
                            data.append(note)
                data.extend([xml.get_ecrit_EAF(cand), xml.get_oral_EAF(cand)])
                cpes = 'cpes' in xml.get_clas_actu(cand).lower()
                data.extend([xml.get_CM1(cand, cpes), xml.get_CP1(cand, cpes)])
                # La suite
                data.extend([fonction(cand) for fonction in [xml.get_scoreb, xml.get_correc, xml.get_scoref,
                xml.get_jury, xml.get_motifs]])
                c.writerow(data)
        # Retour au menu
        cherrypy.session['tableaux'] = 'ok' # Ça c'est pour un message ok !
        return self.retour_menu()


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
