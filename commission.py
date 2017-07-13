#!/usr/bin/env python3
#-*- coding: utf-8 -*-

# Comment cherrypy et le navigateur discutent :
# navigateur --> cherrypy : par l'intermédiaire des formulaires html. Dans la déclaration d'un formulaire,
# un choix method = POST (ou GET) action = nom_d_une_méthode_python qui sera exécutée dès la validation
# du formulaire.
# Une méthode n'est visible par le navigateur que si elle est précédée par @cherrypy.expose
# cherrypy --> navigateur : en retour (par la fonction return), le code python renvoi le code --- sous
# la forme d'une chaine (immense) de caractères --- d'une page html. 
# Ce peut-être la même qui a généré l'appel à cette méhode ou toute autre. 

import os, cherrypy, random, copy, glob, csv, pickle
from parse import parse
from lxml import etree
import utils.interface_xml as xml
import utils.decoupage_pdf as decoup
from utils.apb_csv import lire
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
	# Chargement de tous les "patrons" de pages HTML dans un dictionnaire :
	with open(os.path.join(os.curdir,"utils","patrons.html"),"r") as fi:
		html = {}
		for ligne in fi:
			if ligne.startswith("[*"):	 # étiquette trouvée ==>
				label =ligne.strip()	 # suppression LF et esp évent.
				label =label[2:-2]	 # suppression [* et *]
				txt =""
			else:
				if ligne.startswith("#####"):
					html[label] =txt
				else:
					txt += ligne
	
	# Fin variables de classe

	# constructeur
	def __init__(self,key,droits):
		self.je_suis = key
		self.dossiers = []
		self.num_doss = 0
		self.fichier = ''
		self.droits = droits
		self.filiere = ''
	
	def get_je_suis(self):
		return self.je_suis
	
	def get_cand_cour(self): # retourne le candidat courant
		return self.dossiers[self.num_doss]
	
	def get_dossiers(self):
		return self.dossiers

	def set_num_doss(self,num):
		self.num_doss = num
	
	def get_num_doss(self):
		return self.num_doss
	
	def set_fichier(self,fich):
		self.fichier = fich
	
	def set_droits(self,droits):
		self.droits = droits
	
	def get_droits(self):
		return self.droits
	
	def set_filiere(self,fil):
		self.filiere = fil
	
	def get_filiere(self):
		return self.filiere

	def mise_en_page_menu(self,header,contenu):
		# Fonction de "mise en page" du code HTML généré : renvoie une page HTML
		# avec un header et un contenu (dossier, liste, script) adéquats.
		data = {'header':header,'contenu':contenu}
		return Client.html["MEP_MENU"].format(**data)
	
	def mise_en_page(self,visib,header,dossier='',liste=''):
		# Fonction de "mise en page" du code HTML généré : renvoie une page HTML
		# avec un header et un contenu (dossier, liste, script) adéquats.
		data = {'header':header,'dossier':dossier,'liste':liste,'visibilite':visib}
		return Client.html["miseEnPage"].format(**data)
	
	def lire_fichier(self):
		# Lit le fichier XML choisi et vérifie la complétude des dossiers
		# Les données candidats sont récupérées depuis un fichier xml.
		self.dossiers = etree.parse(self.fichier).getroot()

	def sauvegarder(self):
		# Sauvegarde le fichier traité (appelé par la fonction traiter)
		# fonction qui met à jour (par écrasement) le fichier xml contenant les dossiers
		with open(self.fichier, 'wb') as fich:
			fich.write(etree.tostring(self.dossiers, pretty_print=True, encoding='utf-8'))
	
	def genere_header(self): 
		# Génère l'entête de page HTML
		# comme son nom l'indique, cette fonction génère une chaine de caractères qui est le code html du header...
		sous_titre = ' - Accès {}.'.format(self.droits)
		return '<h1 align="center">EPA - Recrutement CPGE/CPES {}</h1>'.format(sous_titre)

########################################################################
#                        Class Jury                                    #
########################################################################

class Jury(Client): # Objet client (de type jury de commission)  pour la class Serveur

	# constructeur
	def __init__(self,key):
		Client.__init__(self,key,'Jury')
	
	def set_droits(self,droits):
		Client.set_droits(self,'Jury '+droits)

	def mise_en_page(self,header,dossier='',liste=''):
		# Fonction de "mise en page" du code HTML généré : renvoie une page HTML
		# avec un header et un contenu (dossier, liste, script) adéquats.
		return Client.mise_en_page(self,'none',header,dossier,liste)
	
	def genere_menu(self):
		data = {}
		txt = self.genere_liste_comm()
		if txt != '':
			txt = '<h2>Veuillez sélectionner le fichier que vous souhaitez traiter.</h2>'+txt
		data['liste'] = txt
		return self.mise_en_page_menu(self.genere_header(),Client.html["menu_comm"].format(**data))

	def genere_liste_comm(self):
		# Compose le menu commission
		list_fich = glob.glob(os.path.join(os.curdir,"data","epa_comm_*.xml"))
		txt = ''
		for fich in list_fich:
			txt += '<input type="submit" class = "fichier" name="fichier" value="{}"/>'.format(fich)
			txt += '<br>'
		return txt
	
	def traiter(self, **kwargs):
		cand = self.dossiers[self.num_doss]
		# 1/ correc et scoref
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
		# Qui a traité le dossier
		xml.set_jury(cand,self.droits)
		# 3/ "bouléen" traite : dossier traité
		xml.set_traite(cand)
		# 4/ motif
		xml.set_motifs(cand, kwargs['motif'])
		# On sélectionne le dossier suivant
		if self.num_doss < len(self.dossiers)-1:
			self.num_doss = self.num_doss+1

########################################################################
#                        Class Admin                                   #
########################################################################

class Admin(Client): # Objet client (de type Administrateur) pour la class Serveur

	def __init__(self,key):
		# constructeur
		Client.__init__(self,key,'Administrateur')
		self.autres_filieres = []
		self.fichiers_autres_fil = []
		self.dossiers_autres_fil = []
		self.toutes_cand = []
	
	def set_droits(self,droits):
		Client.set_droits(self,'Administrateur '+droits)
	
	def mise_en_page(self,header,dossier='',liste=''):
		# Fonction de "mise en page" du code HTML généré : renvoie une page HTML
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
			with open(os.path.join(os.curdir,"data","stat"), 'br') as fich:
				stat = pickle.load(fich)
			# Création de la liste
			liste_stat = '<h3>Statistiques :</h3>'
			liste_stat += '<ul><li>{} dossiers MPSI</li>'.format(stat['M'])
			liste_stat += '<li>{} dossiers PCSI</li>'.format(stat['P'])
			liste_stat += '<li>{} dossiers CPES</li>'.format(stat['C'])
			liste_stat += 'dont :'
			liste_stat += '<ul><li>{} dossiers MPSI + PCSI</li>'.format(stat['MP'])
			liste_stat += '<li>{} dossiers MPSI + CPES</li>'.format(stat['MC'])
			liste_stat += '<li>{} dossiers PCSI + CPES</li>'.format(stat['PC'])
			liste_stat += '<li>{} dossiers MPSI + PCSI + CPES</li></ul></ul>'.format(stat['MPC'])
		return liste_stat

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
		# Dossiers
		self.dossiers_autres_fil = [etree.parse(fich).getroot() for fich in self.fichiers_autres_fil]
		# Candidatures
		self.toutes_cand = [self.dossiers[self.num_doss]] # 1ere candidature = candidature en cours..
		self.toutes_cand.extend([root.xpath('./candidat/id_apb[text()={}]'.format(iden))[0].getparent() for root in self.dossiers_autres_fil if root.xpath('./candidat/id_apb[text()={}]'.format(iden))])

	def traiter(self, **kwargs):
		# Traitement dossier avec droits administrateur	
		cand = self.dossiers[self.num_doss]
		# Droits admin : on ne prend pas en compte les corrections et motivations

		# Ici, on va répercuter les complétions de l'administrateur dans tous les dossiers que le
		# candidat a déposé. 

		# Recherche des autres candidatures : renvoie une liste (éventuellement vide) de candidature
		self.get_toutes_cand()

		# Admin a-t-il changé qqc ? Si oui, mise à jour. 
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
			for ca in self.toutes_cand: xml.set_ecrit_EAF(ca,kwargs['EAF_e'])
		if xml.get_oral_EAF(cand)!=kwargs['EAF_o']:
			for ca in self.toutes_cand: xml.set_oral_EAF(ca,kwargs['EAF_o'])
		# On (re)calcule le score brut !
		xml.calcul_scoreb(cand)
		xml.is_complet(cand) # mise à jour de l'état "dossier complet"

		# Sauvegarde autres candidatures
		for i in range(0,len(self.fichiers_autres_fil)):
			with open(self.fichiers_autres_fil[i], 'wb') as fich:
				print('fichier écrit : ',fich)
				fich.write(etree.tostring(self.dossiers_autres_fil[i], pretty_print=True, encoding='utf-8'))
	
	def lire_fichier(self): # Comment on dit déjà : écrire par dessus la méthode de la classe mère...
		# Lit le fichier XML choisi et vérifie la complétude des dossiers
		# Les données candidats sont récupérées depuis un fichier xml.
		Client.lire_fichier(self)
		for cand in self.dossiers:
			xml.is_complet(cand) # on renseigne le noeud complet (oui/non)

########################################################################
#                        Class Serveur                                 #
########################################################################

class Serveur(): # Objet lancé par cherrypy dans le __main__
	"Classe générant les objets gestionnaires de requêtes HTTP"
	
	# Attributs de classe
	# faire attention que 0 soit dans la liste !!
	corrections = [(n+min_correc*nb_correc)/float(nb_correc) for n in range(0,(max_correc-min_correc)*nb_correc+1)]
	# Fin déclaration attributs de classe

	def __init__(self):
		# constructeur
		self.clients = {}
	
	def get_client_cour(self):
		return self.clients[cherrypy.session["JE"]]

	def get_cand_cour(self):
		return self.get_client_cour().get_cand_cour()
	
	@cherrypy.expose
	def index(self):
		# Page d'entrée du site web - renvoi d'une page HTML
		data = {'header':self.genere_header(),'contenu':Client.html["pageAccueil"].format('')}
		return Client.html["MEP_MENU"].format(**data)
  
	@cherrypy.expose
	def identification(self, **kwargs):
		# Admin ou Jury : fonction appelée par le formulaire de la page d'accueil. 
		# On créé une clé client_i (stockée dans les cookies de session) et l'objet associé est Admin ou Jury
		key = 'client_{}'.format(len(self.clients)+1)
		cherrypy.session['JE'] = key # Le client stocke qui il est
		if kwargs['acces']=="Accès administrateur":
			self.clients[key] = Admin(key)
		else:
			self.clients[key] = Jury(key)
		return self.clients[key].genere_menu()

	@cherrypy.expose
	def retour_menu(self):
		# Retour menu 
		return self.get_client_cour().genere_menu()
	
	def efface_dest(self,chem): # sert dans traiter_csv et dans tableaux/bilans
		# Efface les dossiers qui accueilleront les bulletins
		for filename in os.listdir(chem):
			fich = os.path.join(chem,filename)
			try:
				os.remove(fich)
			except: # cas d'un sous-dossier
				self.efface_dest(fich)
				os.rmdir(fich)

	def trouve(self, iden, num_fil, cc, root, fil):
		# Sous-fonction de la fonction stat...
		if num_fil < len(root)-1:
			cand = root[num_fil+1].xpath('./candidat/id_apb[text()={}]'.format(iden))
			if cand:
				cc += fil[num_fil + 1]
			else:
				cc += '-'
			cc = self.trouve(iden, num_fil + 1, cc, root, fil)
			if cand: xml.set_candidatures(cand[0].getparent(), cc)
		return cc
			
	def stat(self):
		# Effectue des statistiques sur les candidats
		list_fich = glob.glob(os.path.join(os.curdir,"data","epa_admin_*.xml"))

		root = [etree.parse(fich).getroot() for fich in list_fich]
		fil = [parse(os.path.join(os.curdir,"data","epa_admin_{}.xml"),fich)[0][0] for fich in list_fich]

		# Initialisation des compteurs
		num = [0]*len(root) # nombres de candidats par filière
		num_mp = 0 # 4 compteurs spécifiques aux filières EPA...
		num_mc = 0
		num_pc = 0
		num_mpc = 0
	
		for i in range(len(root)): # num filière
			for candi in root[i]:
				num[i] += 1
				if xml.get_candidatures(candi) == '???': # candidat pas encore vu
					iden = xml.get_id(candi)
					cc = '-'*i + fil[i]
					cc = self.trouve(iden, i, cc, root, fil) 
					xml.set_candidatures(candi,cc)
					if cc == 'CMP': num_mpc += 1 # 4 lignes qui sont spécifiques aux filières EPA...
					if cc == 'CM-': num_mc += 1
					if cc == 'C-P': num_pc += 1
					if cc == '-MP': num_mp += 1
		# Sauvegarder
		for i in range(len(root)):
			with open(list_fich[i], 'wb') as fi:
				fi.write(etree.tostring(root[i], pretty_print=True, encoding='utf-8'))
		
		# Écrire le fichier stat
		donnees = {fil[i]:num[i] for i in range(0,len(fil))}
		donnees.update({'MP':num_mp,'MC':num_mc,'PC':num_pc,'MPC':num_mpc})
		with open(os.path.join(os.curdir,"data","stat"),'wb') as stat_fich:
			pickle.dump(donnees,stat_fich)
			
	@cherrypy.expose
	def traiter_apb(self): 
		# Traite les données brutes d'APB : csv ET pdf
		## Traitement des csv ##
		for doc in glob.glob(os.path.join(os.curdir,"data","*.csv")):
			for fil in filieres:
				if fil in doc.lower():
					dest = os.path.join(os.curdir,"data","epa_admin_{}.xml".format(fil.upper()))
			xml = lire(doc)
			with open(dest, 'wb') as fich:
				fich.write(etree.tostring(xml, pretty_print=True, encoding='utf-8'))
		## Traitement des pdf ##
		dest = os.path.join(os.curdir,"data","docs_candidats")
		try:
			self.efface_dest(dest) # on efface toute l'arborescence fille de dest 
		except: # dest n'existe pas !
			os.mkdir(dest) # on le créé...
		
		for fich in glob.glob(os.path.join(os.curdir,"data","*.pdf")):
			for fil in filieres:
				if fil in fich.lower():
					desti = os.path.join(dest,fil)
					os.mkdir(desti)
					decoup.decoup(fich, desti)
		# Fin du traitement pdf#
		# Faire des statistiques
		self.stat()
		# Fin
		return self.get_client_cour().genere_menu()
	
	@cherrypy.expose
	def choix_comm(self, **kwargs):
		# Gère le choix fait dans le menu commission
		# récupère le client
		client = self.get_client_cour()
		# Mise à jour des attributs du client
		client.set_fichier(kwargs["fichier"])
		r = parse('{}comm_{}{:d}.xml', kwargs["fichier"]) # récupère nom commission
		client.set_droits(r[1] + str(r[2]))
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
		# récupère le client
		client = self.get_client_cour()
		# Mise à jour des attributs du client
		client.set_fichier(kwargs["fichier"])
		r = parse('{}admin_{}.xml', kwargs["fichier"]) # récupère nom commission
		client.set_droits(r[1])
		client.set_filiere(r[1].lower())
		# Ici, on va charger les dossiers présents dans le fichier choisi :
		client.lire_fichier()
		# Initialisation des paramètres
		client.set_num_doss(0) # on commence par le premier !
		cherrypy.session['mem_scroll'] = '0'
		# Affichage de la page de gestion des dossiers
		return self.affi_dossier()		
	
	# Fonction qui génère la page html contenant les dossiers
	@cherrypy.expose
	def affi_dossier(self):
		# Renvoi d'une page HTML, formatée avec le nom de la commission :
		# Quel client ?
		client = self.get_client_cour()
		# Quels droits ?
		droits = self.get_client_cour().get_droits()
		# Quel candidat ?
		cand = self.get_cand_cour()
		# On génère les 3 parties de la page html
		self.header = self.genere_header()
		self.dossier = self.genere_dossier(cand, droits)
		self.liste = self.genere_liste()
		# On retourne cette page au navigateur
		return client.mise_en_page(self.header,self.dossier,self.liste)

	
	@cherrypy.expose
	def traiter(self, **kwargs):
		# Fonction appelée par l'appui sur "VALIDER" : valide les choix commission ou Admin
		# Cette méthode est appelée par le bouton valider de la page dossier...
		# **kwargs empaquette les arguments passés par le navigateur dans le dictionnaire kwargs..
		# mise à jour dans les variables de session du dossier du candidat...
		client = self.get_client_cour()
		client.traiter(**kwargs)
		## Et on sauvegarde immédiatement tout cela...
		client.sauvegarder()
		# Et on retourne au traitement...
		return self.affi_dossier()
		
	@cherrypy.expose
	def click_list(self,**kwargs):
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
		data = {'Nom':xml.get_nom(cand)+', '+xml.get_prenom(cand)}
		data['naiss'] = xml.get_naiss(cand)
		data['etab'] = xml.get_etab(cand)
		txt = '[{}]-{}'.format(xml.get_id(cand),xml.get_INE(cand))
		data['id'] = txt
		# récup filiere
		fil = self.get_client_cour().get_filiere()
		data['ref_fich'] = os.path.join('docs_candidats','{}'.format(fil),'docs_{}'.format(xml.get_id(cand)))
		if 'admin' in droits.lower():
			clas_inp = '<input type="text" id="clas_actu" name = "clas_actu" size = "10" value="{}"/>'.format(xml.get_clas_actu(cand))
			data['clas_actu'] = clas_inp
		else:
			data['clas_actu'] = xml.get_clas_actu(cand)
		# Cases à cocher semestres : actives pour l'Admin, inactives sinon
		visib = 'disabled '
		if 'admin' in droits.lower():
			visib = ' '
		txt = visib
		if xml.get_sem_prem(cand)=='on': txt += 'checked'
		data['sem_prem'] = txt
		txt = visib
		if xml.get_sem_term(cand)=='on': txt += 'checked'
		data['sem_term'] = txt
		# Notes
		matiere = {'M':'Mathématiques','P':'Physique/Chimie'}
		date = {'1':'trimestre 1','2':'trimestre 2','3':'trimestre 3'}
		classe = {'P':'Première','T':'Terminale'}
		for cl in classe:
			for mat in matiere:
				for da in date:
					key = cl + mat + da
					note = '{}'.format(xml.get_note(cand, classe[cl], matiere[mat],date[da]))
					note_inp = '<input type = "text" class = "notes grossi" id = "{}" name = "{}" value = "{}"/>'.format(key,key,note)
					if 'admin' in droits.lower():
						data[key] = note_inp
					else:
						data[key] = note
		# CPES
		cpes = False
		if 'cpes' in xml.get_clas_actu(cand).lower():
			cpes = True
		if 'admin' in droits.lower():
			note_CM1 = '<input type = "text" class = "notes grossi" id = "CM1" name = "CM1" value = "{}"/>'.format(xml.get_CM1(cand,cpes))
			data['CM1'] = note_CM1
			note_CP1 = '<input type = "text" class = "notes grossi" id = "CP1" name = "CP1" value = "{}"/>'.format(xml.get_CP1(cand,cpes))
			data['CP1'] = note_CP1
		else:
			data['CM1'] = '{}'.format(xml.get_CM1(cand,cpes))
			data['CP1'] = '{}'.format(xml.get_CP1(cand,cpes))
		# EAF
		if 'admin' in droits.lower():
			note_eaf_e = '<input type = "text" class = "notes grossi" id = "EAF_e" name = "EAF_e" value = "{}"/>'.format(xml.get_ecrit_EAF(cand))
			data['EAF_e'] = note_eaf_e
			note_eaf_o = '<input type = "text" class = "notes grossi" id = "EAF_o" name = "EAF_o"value = "{}"/>'.format(xml.get_oral_EAF(cand))
			data['EAF_o'] = note_eaf_o
		else: 
			data['EAF_e'] = xml.get_ecrit_EAF(cand)
			data['EAF_o'] = xml.get_oral_EAF(cand)		
		# Suite
		data['scoreb'] = xml.get_scoreb(cand)
		data['scoref'] = xml.get_scoref(cand)
		data['cand'] = xml.get_candidatures(cand,'impr')
		return data
	
	def genere_header(self): 
		# Génère l'entête de page HTML
		# comme son nom l'indique, cette fonction génère une chaine de caractères qui est le code html du header...
		qui = cherrypy.session.get('JE','') 
		sous_titre = ''
		if qui !='': # sur la page d'accueil, pas de sous-titre...
			sous_titre = ' - Accès {}.'.format(self.clients[qui].get_droits())
		return '<h1 align="center">EPA - Recrutement CPGE/CPES {}</h1>'.format(sous_titre)
	
	
	# Génère la partie dossier de la page HTML
	def genere_dossier(self, cand, droits): # fonction générant le code html du dossier
		# récupération correction
		correc = str(xml.get_correc(cand))
		ncval = ''
		if correc == 'NC': 
			correc = 0
			ncval = 'NC'
		# Construction de la barre de correction :
		barre = '<tr><td width = "2.5%"></td><td>'
		barre += '<input type = "range" class = "range" min="-3" max = "3" step = ".25"	name = "correc" id = "correc" onchange="javascript:maj_note();"	onmousemove="javascript:maj_note();" onclick="click_range();" value = "{}"/>'.format(correc)
		barre += '</td><td width = "2.5%"></td></tr>' # fin de la ligne range
		txt = '' # on construit maintenant la liste des valeurs...
		for i in range(0,len(Serveur.corrections)+1):
			if (i % 2 == 0):
				txt += '<td width = "7%">{:+3.1f}</td>'.format(Serveur.corrections[i])
		barre += '<tr><td align = "center" colspan = "3"><table width = "100%"><tr class = "correc_notimpr">{}</tr></table>'.format(txt)
		barre += '<span class = "correc_impr">'+xml.get_jury(cand)+' : {:+.2f}'.format(float(correc))+'</span>'
		barre += '</td></tr>'
		# input hidden nc
		nc = '<input type="hidden" id = "nc"  name = "nc" value = "{}"/>'.format(ncval)
		# Construction de la chaine motifs.
		motifs = ''
		for i in range(0,len(motivations)):
			key = 'mot_'+str(i)
			motifs += '<tr><td align = "left"><input type="button" name="'+key
			motifs += '" id="'+key+'" onclick="javascript:maj_motif(this.id)"'
			motifs += ' class = "motif" value ="'+ motivations[i]+'"/></td></tr>'
		# le dernier motif : autre ... 
		motifs += '<tr><td align = "left">'
		motifs += '<input type="text" class = "txt_motifs" name="motif" id = "motif" value= "'
		try:
			motifs += xml.get_motifs(cand)+'"/>'
		except:
			motifs += '"/>'
		motifs += "</td></tr>"
	
		# On met tout ça dans un dico data pour passage en argument à page_dossier
		data = self.genere_dict(cand, droits) 
		data['barre'] = barre
		data['nc'] = nc
		data['motifs'] = motifs
		return Client.html["page_dossier"].format(**data)
		
	# Génère la partie liste de la page HTML
	def genere_liste(self):
		client = self.get_client_cour()
		liste = client.get_dossiers()
		num_doss = client.get_num_doss()
		# Construction de la chaine lis : code html de la liste des dossiers.
		lis = '<form id = "form_liste" action = "click_list" method=POST>'
		lis += '<input type="hidden" name = "scroll_mem" value = "'
		lis += cherrypy.session['mem_scroll']+'"/>' # mémo du scroll
		for i in range(0,len(liste)):
			lis += '<input type = "submit" name="num" '
			clas = 'doss'
			if i == num_doss: # affecte la class css "doss_courant" au dossier  courant
					clas += ' doss_courant'
			if xml.get_traite(liste[i]) != '':
					clas += ' doss_traite' # affecte la classe css "doss_traite" aux ...
			if client.get_droits() == "Administrateur":
				if xml.get_complet(liste[i])=='non':	# Dossier incomplet (seulement admin ?)
					clas += ' doss_incomplet'
			lis += 'class = "{}"'.format(clas)
			nom = xml.get_nom(liste[i])+', '+xml.get_prenom(liste[i])
			txt = '{:3d}) {: <30}{}'.format(i+1,nom[:29],xml.get_candidatures(liste[i],'ord'))
			lis += ' value="'+txt+'"></input><br>'
		# txt est le txt que contient le bouton. Attention, ses 3 premiers
		# caractères doivent être le numéro du dossier dans la liste des
		# dossiers (client_get_dossiers())... Cela sert dans click_list(), pour identifier sur qui on a clické..
		lis += '-'*7+' fin de liste '+'-'*7
		lis = lis + '</form>'	
		return lis

 	
	@cherrypy.expose
	def genere_fichiers_comm(self):
		# Générer les fichier epa_comm_mpsi1.xml jusqu'à epa_comm_cpesN.xml
		# Récupération des fichiers admin
		list_fich = glob.glob(os.path.join(os.curdir,"data","epa_admin_*.xml"))
 		# Pour chaque fichier "epa_admin_*.xml"
		for fich in list_fich:
			doss = etree.parse(fich).getroot()
			# Tout d'abord, calculer le score brut de chaque candidat 
			for cand in doss:
				xml.calcul_scoreb(cand)
			# Classement par scoreb décroissant
			doss[:] = sorted(doss, key = lambda cand: -float(cand.xpath('diagnostic/score')[0].text.replace(',','.')))
			# Récupération de la filière 
			fil = parse(os.path.join(os.curdir,"data","epa_admin_{}.xml"),fich)
			nbjury = int(nb_jury[fil[0].lower()])
			# Découpage en n listes de dossiers
			for j in range(0,nbjury):
				dossier = []	# deepcopy ligne suivante sinon les candidats sont retirés de doss à chaque append vers dossier
				[dossier.append(copy.deepcopy(doss[i])) for i in range(0,len(doss)) if i%nbjury == j]
				# Sauvegarde
				res = etree.Element('candidats')
				[res.append(cand) for cand in dossier]
				nom = os.path.join(os.curdir,"data","epa_comm_{}{}.xml".format(fil[0],j+1))
				with open(nom, 'wb') as fichier:
					fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
			
		# Enfin, on retourne au menu
		return self.retour_menu()

	# Convertit une date de naissance en un nombre pour le classement
	def convert(self, naiss):
		dic = parse('{j:d}/{m:d}/{a:d}',naiss)
		return dic['a']*10**4+dic['m']*10**2+dic['j']
	
	# Récolter les fichiers après la commission
	@cherrypy.expose
	def genere_fichiers_class(self):
		# Pour chaque filière
		for comm in filieres:
			list_fich = glob.glob(os.path.join(os.curdir,"data","epa_comm_{}*.xml".format(comm.upper())))
			list_doss = [] # contiendra les dossiers de chaque sous-comm
			# Pour chaque sous-commission
			for fich in list_fich:
				# lecture fichier
				doss = etree.parse(fich).getroot()
				# Les fichiers non vus se voient devenir NC avec
				# motifs = "Dossier moins bon que le dernier classé"
				for c in doss:
					if xml.get_jury(c) == 'Auto':
						xml.set_correc(c, 'NC')
						xml.set_scoref(c, 'NC')
						xml.set_motifs(c,'Dossier moins bon que le dernier classé.')
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
					for k in range(1,len(list_doss)): # reste-t-il des candidats classés dans les listes suivantes ?
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
					xml.set_rang(cand,nu)
				# Sauvegarde du fichier class...
				nom = os.path.join(os.curdir,"data","epa_class_{}.xml".format(comm.upper()))
				with open(nom, 'wb') as fichier:
					fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
				
		# Enfin, on retourne au menu
		return self.retour_menu()
	
	@cherrypy.expose
	def page_impression(self, **kwargs):
		# Générer la page html pour impression des fiches bilan de commission
		r = parse('{}class_{}.xml', kwargs["fichier"]) # récupère nom commission
		txt = ''
		for cand in etree.parse(kwargs["fichier"]).getroot():
			if xml.get_scoref(cand) != 'NC':
				txt += '<h1 align="center" class = "titre">EPA - Recrutement CPGE/CPES - {}</h1>'.format(r[1].upper())
				if xml.get_rang(cand) == 'NC':# Ce test est un résidu d'une époque ou on générait une fiche même si le candidat n'était pas classé !
					txt += '<div class = encadre>Candidat non classé</div>'
				else:
					 txt += '<div class = encadre>Candidat classé : {}</div>'.format(xml.get_rang(cand))
				txt += self.genere_dossier(cand,"commission")
				txt += '<div style = "page-break-after: always;"></div>'
		txt = txt[:-len('<div style = "page-break-after: always;"></div>')] # On enlève le dernier saut de page...
		data = {'pages':txt}
		return Client.html['page_impress'].format(**data) 
	
	# Générer les tableaux .csv bilans de la commission
	@cherrypy.expose
	def tableaux_bilan(self):
		# Un peu de ménage...
		dest = os.path.join(os.curdir,"tableaux")
		try:
			self.efface_dest(dest) # on efface toute l'arborescence fille de dest 
		except: # dest n'existe pas !
			os.mkdir(dest) # on le créé...
		# Création du fichier d'aide
		with open(os.path.join(dest,"aide.txt"), 'w') as fi:
			txt = ("En cas de difficultés à ouvrir les .csv avec EXCEL,\n"
			"il est conseillé d'utiliser la fonction fichier-->importer")
			fi.write(txt)
		fi.close()
		# Récupération des fichiers
		list_fich = glob.glob(os.path.join(os.curdir,"data","epa_class_*.xml"))
		# Pour chaque filière :
		for fich in list_fich:
			# lecture fichier
			doss = etree.parse(fich).getroot()
			# 1er tableau : liste ordonnée des candidats retenus, pour Jeanne
			nom = os.path.join(os.curdir,"tableaux","") # chaîne vide pour avoir / à la fin du chemin...
			nom += parse(os.path.join(os.curdir,"data","epa_class_{}.xml"),fich)[0]
			nom += '_retenus.csv'
			c = csv.writer(open(nom,'w'))
			entetes = ['Rang','Nom','Prénom','Date de naissance','score brut','correction','score final','jury','Observations']
			c.writerow(entetes)
			for cand in doss:
				if xml.get_scoref(cand) != 'NC': # seulement les classés !!
					data = [fonction(cand) for fonction in [xml.get_rang,xml.get_nom,xml.get_prenom,xml.get_naiss,xml.get_scoreb,xml.get_correc,xml.get_scoref,xml.get_jury,xml.get_motifs]]
					c.writerow(data)
			# 2e tableau : liste ordonnée des candidats retenus, pour Bureau des élèves
			# Le même que pour Jeanne, mais sans les notes...
			nom = os.path.join(os.curdir,"tableaux","") # chaîne vide pour avoir / à la fin du chemin..
			nom += parse(os.path.join(os.curdir,"data","epa_class_{}.xml"),fich)[0]
			nom += '_retenus(sans_note).csv'
			c = csv.writer(open(nom,'w'))
			entetes = ['Rang','Nom','Prénom','Date de naissance']
			c.writerow(entetes)
			for cand in doss:
				if xml.get_scoref(cand) != 'NC': # seulement les classés !!
					data = [fonction(cand) for fonction in [xml.get_rang,xml.get_nom,xml.get_prenom,xml.get_naiss]]
					c.writerow(data)
			# 3e tableau : Liste alphabétique de tous les candidats avec le numéro dans le classement,
			# toutes les notes et qq infos administratives
			# Fichier destination
			nom = os.path.join(os.curdir,"tableaux","") # chaîne vide pour avoir / à la fin du chemin...
			nom += parse(os.path.join(os.curdir,"data","epa_class_{}.xml"),fich)[0]
			nom += '_alphabetique.csv'
			c = csv.writer(open(nom,'w'))
			entetes = ['Rang','Candidatures','Nom','Prénom','Date de naissance','Sexe','Nationalité','id_apb','Boursier','Classe actuelle','Etablissement','Commune Etablissement']
			# entêtes notes...
			matiere = {'M':'Mathématiques','P':'Physique/Chimie'}
			date = {'1':'trimestre 1','2':'trimestre 2','3':'trimestre 3'}
			classe = {'P':'Première','T':'Terminale'}
			entetes.extend([cl + mat + da for cl in classe for da in date for mat in matiere])
			entetes.extend(['F_écrit','F_oral','CPES_math','CPES_phys'])
			# la suite
			entetes.extend(['score brut','correction','score final','jury','Observations'])
			c.writerow(entetes)
			# Classement alphabétique
			doss[:] = sorted(doss, key = lambda cand: xml.get_nom(cand))
			# Remplissage du fichier dest
			for cand in doss:
				data = [xml.get_rang(cand), xml.get_candidatures(cand,'ord')]
				data += [fonction(cand) for fonction in [xml.get_nom,xml.get_prenom,xml.get_naiss,xml.get_sexe,xml.get_nation,xml.get_id,xml.get_boursier,xml.get_clas_actu,xml.get_etab,xml.get_commune_etab]]
				# Les notes...
				for cl in classe:
					for da in date:
						for mat in matiere:
							key = cl + mat + da
							note = '{}'.format(xml.get_note(cand, classe[cl], matiere[mat],date[da]))
							data.append(note)
				data.extend([xml.get_ecrit_EAF(cand),xml.get_oral_EAF(cand)])
				cpes = 'cpes' in xml.get_clas_actu(cand).lower()
				data.extend([xml.get_CM1(cand,cpes),xml.get_CP1(cand,cpes)])
				# La suite
				data.extend([fonction(cand) for fonction in [xml.get_scoreb,xml.get_correc,xml.get_scoref,xml.get_jury,xml.get_motifs]])
				c.writerow(data)
		# Retour au menu
		cherrypy.session['tableaux'] = 'ok' # Ça c'est pour un message ok !
		return self.retour_menu()


########################################################################
#                    === PROGRAMME PRINCIPAL ===                       #
########################################################################

# Reconfiguration et démarrage du serveur web :
cherrypy.config.update({"tools.staticdir.root":os.getcwd()})
cherrypy.quickstart(Serveur(),'/', config ="utils/config.conf")
