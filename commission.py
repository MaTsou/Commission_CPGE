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

import os, cherrypy, random, copy, glob, csv
from parse import parse
from lxml import etree
import utils.interface_xml as xml
import utils.decoupage_pdf as decoup
from utils.apb_csv import lire
from utils.parametres import motifs
from utils.parametres import min_correc
from utils.parametres import max_correc
from utils.parametres import nb_correc
from utils.parametres import filieres
from utils.parametres import nb_jury


def charger_correc():
	NB = (max_correc-min_correc)*nb_correc+1 # nb valeurs correction
	pas_correc = 1/float(nb_correc)
	 # faire attention que 0 soit dans la liste !!
	correc = []
	for n in range(0,NB):
		correc.append((n+min_correc*nb_correc)*pas_correc)
	return correc

def charger_motifs():
	motiv = {}
	for mot in motifs:
		key = 'mot_{:d}'.format(motifs.index(mot))
		motiv.update({key:mot})
	return motiv
	      
def chargerPatronsHTML():
		# Chargement de tous les "patrons" de pages HTML dans un dictionnaire :
		fi =open("utils/patrons.htm","r")
		html = {}
		try:	       # pour s'assurer que le fichier sera toujours refermé
			for ligne in fi:
				if ligne[:2] =="[*":	    # étiquette trouvée ==>
					label =ligne[2:]	    # suppression [*
					label =label[:-1].strip()	 # suppression LF et esp évent.
					label =label[:-2]	    # suppression *]
					txt =""
				else:
					if ligne[:5] =="#####":
						html[label] =txt
					else:
						txt += ligne
		finally:
			fi.close()       # fichier refermé dans tous les cas
		return html
      
def mep(header,dossier='',liste=''):
	# Fonction de "mise en page" du code HTML généré : renvoie une page HTML
	# avec un header et un contenu (dossier, liste, script) adéquats.
	data = {'header':header,'dossier':dossier,'liste':liste}
	info = '' # texte sous le bouton "gros_bout" au-dessus de la liste de dossiers
	if cherrypy.session['droits'] == 'administrateur':
		visib = ''
	else:
		visib = 'none' # Bouton pas affiché dans la vue commission
	data.update({'visibilite':visib})
	return html["miseEnPage"].format(**data)

def mep_menu(header,contenu):
	# Fonction de "mise en page" du code HTML généré : renvoie une page HTML
	# avec un header et un contenu (dossier, liste, script) adéquats.
	data = {'header':header,'contenu':contenu}
	return html["MEP_MENU"].format(**data)
	
########################################################################
#                        Class commission                              #
########################################################################

class Commission(object): # Objet lancé par cherrypy dans le __main__
	"Classe g&eacute;n&eacute;rant les objets gestionnaires de requ&ecirc;tes HTTP"
 	
 	# Page d'accueil
	@cherrypy.expose
	def index(self):
		cherrypy.session['droits']=''
		# Page d'entrée du site web - renvoi d'une page HTML statique :
		return mep_menu(self.genere_header(),html["pageAccueil"].format(''))
  
	# Admin ou Commission : fonction appelée par le formulaire de la page d'accueil. 
	@cherrypy.expose
	def identification(self, **kwargs):
		# On mémorise les coord. de l'utilisat. dans des variables de session :
		if kwargs['acces']=="Accès administrateur":  
			cherrypy.session['droits'] = 'administrateur'
			data = self.genere_menu_admin()
			txt = "menu_admin_{}".format(data['menu'])
			return mep_menu(self.genere_header(),html[txt].format(**data))
		else:
			cherrypy.session['droits'] = 'commission'
			data = {}
			txt = self.genere_liste_comm()
			if txt != '':
				txt = '<h2>Veuillez sélectionner le fichier que vous souhaitez traiter.</h2>'+txt
			data.update({'liste':txt})
			return mep_menu(self.genere_header(),html["menu_comm"].format(**data))
	
	# Retour menu admin
	@cherrypy.expose
	def retour_menu_admin(self):
		data = {'acces':'Accès administrateur'}
		return self.identification(**data)
	
	# Compose le menu administrateur
	def genere_menu_admin(self):
		data = {}
		# Quel menu : avant commission ou après ??
		chemin = "./data/epa_comm_*.xml"
		list_fich = glob.glob(chemin)
		if len(list_fich) > 0: # après commission
			data.update({'menu':'apres'})
			# Etape 4 bouton
			txt = ''
			if len(self.genere_liste_comm()) > 0:
				txt = '<input type = "button" class ="fichier" value = "Récolter les fichiers" onclick = "recolt_wait();">'
			data.update({'bout_etap4':txt})
			# Etape 5 bouton
			chemin = "./data/epa_class_*.xml"
			list_fich = glob.glob(chemin)
			txt = ''
			if len(list_fich) > 0:
				txt = self.genere_liste_impression()
			data.update({'liste_impression':txt})
			# Etape 6 bouton
			txt = ''
			if len(list_fich) > 0:
				txt = '<form id = "tableaux" action = "/tableaux_bilan" \
					method = POST align = "center">\
					<input type = "button" class = "fichier" name = "tableaux" \
					value = "Générer les tableaux bilan" onclick = "tableaux_wait();"\
					></form>'
				try:
					if cherrypy.session['tableaux'] == 'ok':
						txt += '<p>Ceux-ci sont disponibles dans le dossier "./tableaux"...'
				except:
					pass
			data.update({'form_tableaux':txt})
		
		else: # avant commission
			data.update({'menu':'avant'})
			# liste csv
			data.update({'liste_csv':self.genere_liste_csv()})
			# liste pdf
			data.update({'liste_pdf':self.genere_liste_pdf()})
			# liste admin
			data.update({'liste_admin':self.genere_liste_admin()})
			# liste_stat
			data.update({'liste_stat':self.genere_liste_stat()})
			# Etape 3 bouton
			txt = ''
			if len(self.genere_liste_admin()) > 0:
				txt = '<input type = "button" class ="fichier" value = "Générer les fichiers commission" onclick = "genere_wait();">'
			data.update({'bout_etap3':txt})
		return data

	# Efface les dossiers qui accueilleront les bulletins
	def efface_dest(self,chem): # sert dans traiter_csv et dans tableaux/bilans
		for filename in os.listdir(chem):
			try:
				os.remove(chem+'/'+filename)
			except: # cas d'un sous-dossier
				self.efface_dest(chem+'/'+filename)
				os.rmdir(chem+'/'+filename)

	# Sous-fonction de la fonction stat...
	def trouve(self, id, num_fil, cc, root, fil):
		if num_fil < len(root)-1:
			cand = root[num_fil+1].xpath('./candidat/id_apb[text()={}]'.format(id))
			if cand:
				cc += fil[num_fil + 1]
				xml.set_candidatures(cand[0].getparent(), cc)
			else:
				cc += '-'
			cc = self.trouve(id, num_fil + 1, cc, root, fil)
		return cc
			
	# Effectue des statistiques sur les candidats
	def stat(self):
		chemin = './data/epa_admin_*.xml'
		list_fich = glob.glob(chemin)

		root = []
		[root.append(etree.parse(fich).getroot()) for fich in list_fich]
		fil = []
		[fil.append(parse('./data/epa_admin_{}.xml',fich)[0][0]) for fich in list_fich]

		# on réordonne comme on a l'habitude... MPC plutôt que CMP
		root[:] = root[1:]+root[:1]
		fil[:] = fil[1:]+fil[:1]		
		
		# Initialisation des compteurs
		num = [0 for i in range(len(root))] # nombres de candidats par filière
		num_mp = 0
		num_mc = 0
		num_pc = 0
		num_mpc = 0
	
		for i in range(len(root)): # num filière
			for candi in root[i]:
				num[i] += 1
				if xml.get_candidatures(candi) == '???': # candidat pas encore vu
					id = xml.get_id(candi)
					cc = '-'*i + fil[i]
					cc = self.trouve(id, i, cc, root, fil) 
					xml.set_candidatures(candi,cc)
					if cc == 'MPC': num_mpc += 1
					if cc == 'M-C': num_mc += 1
					if cc == '-PC': num_pc += 1
					if cc == 'MP-': num_mp += 1
		# Sauvegarder
		# Attention, on avait permuté !!!
		root[:] = root[-1:]+root[:-1]
		
		for i in range(len(root)):
			with open(list_fich[i], 'wb') as fi:
				fi.write(etree.tostring(root[i], pretty_print=True, encoding='utf-8'))
		
		# Écrire le fichier stat
		nom = "./data/stat.txt"
		with open(nom ,'w') as stat_fich:
			for i in range(len(fil)):
				stat_fich.write('{}={};'.format(fil[i],num[i]))
			stat_fich.write('MP={};MC={};PC={};'.format(num_mp,num_mc,num_pc))
			stat_fich.write('MPC={}'.format(num_mpc))
		stat_fich.close()
			
	# Traite les données brutes d'APB : csv ET pdf
	@cherrypy.expose
	def traiter_apb(self): # traite aussi les pdf...
	## Traitement des csv ##
		# Traitement des csv
		docs = glob.glob("./data/*.csv")
		for doc in docs:
			for fil in filieres:
				if fil in doc.lower():
					dest = './data/epa_admin_{}.xml'.format(fil.upper())
			xml = lire(doc)
			with open(dest, 'wb') as fich:
				fich.write(etree.tostring(xml, pretty_print=True, encoding='utf-8'))
		# Traitement des pdf ##
		dest = './data/docs_candidats'
		try:
			self.efface_dest(dest) # on efface toute l'arborescence fille de chemin
		except: # dest n'existe pas !
			os.mkdir(dest) # on le créé...
		
		sourc = glob.glob("./data/*.pdf")
		for file in sourc:
			for fil in filieres:
				if fil in file.lower():
					desti = dest+'/'+fil
					os.mkdir(desti)
					decoup.decoup(file, desti)
		# Fin du traitement pdf#
		# Faire des statistiques
		self.stat()
		# Fin
		data = {'acces':'Accès administrateur'}
		return self.identification(**data)	
		
	# Sous-fonction pour le menu admin
	def genere_liste_csv(self):
		list_fich = glob.glob("./data/*.csv")
		txt = ''
		for fich in list_fich:
			txt += '{}<br>'.format(fich)
		return txt
	
	# Sous-fonction pour le menu admin
	def genere_liste_pdf(self):
		list_fich = glob.glob("./data/*.pdf")
		txt = ''
		for fich in list_fich:
			txt += '{}<br>'.format(fich)
		return txt
	
	# Sous-fonction pour le menu admin
	def genere_liste_admin(self):
		chemin = "./data/epa_admin_*.xml"
		list_fich = glob.glob(chemin)
		txt = ''
		if len(list_fich) > 0:
			txt = '<h2>Choisissez le fichier que vous souhaitez compléter</h2>'
		for fich in list_fich:
			txt += '<input type="submit" class = "fichier" name="fichier" value={}>'.format(fich)
			txt += '<br>'
		return txt
	
	# Sous-fonction pour le menu admin
	def genere_liste_stat(self):
		chemin = "./data/epa_admin_*.xml"
		list_fich = glob.glob(chemin)
		liste_stat = ''
		if len(list_fich) > 0:
			# lecture du fichier stat
			nom = './data/stat.txt'
			fich = open(nom,'r')
			txt = fich.read()
			fich.close()
			stat = parse('M={M};P={P};C={C};MP={MP};MC={MC};PC={PC};MPC={MPC}',txt)
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

	# Sous-fonction pour le menu admin
	def genere_liste_impression(self):
		chemin = "./data/epa_class_*.xml"
		list_fich = glob.glob(chemin)
		txt = ''
		if len(list_fich) > 0:
			txt = '<h2>Choisissez le fichier que vous souhaitez imprimer</h2>'
		for fich in list_fich:
			txt+= '<input type = "submit" class ="fichier" name = "fichier" value = {}>'.format(fich)
			txt+='<br>'
		return txt
	
	# Compose le menu commission
	def genere_liste_comm(self):
		chemin = "./data/epa_comm_*.xml"
		list_fich = glob.glob(chemin)
		txt = ''
		for fich in list_fich:
			txt += '<input type="submit" class = "fichier" name="fichier" value={}>'.format(fich)
			txt += '<br>'
		return txt
	
	# Gère le choix fait dans le menu commission
	@cherrypy.expose
	def choix_comm(self, **kwargs):
		cherrypy.session["fichier"] = kwargs["fichier"]
		r = parse('{}comm_{}{:d}.xml', kwargs["fichier"]) # récupère nom commission
		cherrypy.session["droits"] = 'commission '+ r[1] + str(r[2])
		cherrypy.session["filiere"] = r[1].lower()
		# Ici, on va charger les dossiers présents dans le fichier choisi :
		cherrypy.session["dossiers"] = self.lire_fichier()
		cherrypy.session['num_doss'] = 0 # on commence par le premier !
		cherrypy.session['mem_scroll'] = '0'
		# Affichage de la page de gestion des dossiers
		return self.affi_dossier()		
	
	# Gère le choix fait dans le menu admin
	@cherrypy.expose
	def choix_admin(self, **kwargs):
		cherrypy.session["fichier"] = kwargs["fichier"]
		r = parse('{}admin_{}.xml', kwargs["fichier"]) # récupère nom commission
		cherrypy.session["filiere"] = r[1].lower()
		# Ici, on va charger les dossiers présents dans le fichier choisi :
		cherrypy.session["dossiers"] = self.lire_fichier()
		cherrypy.session['num_doss'] = 0 # on commence par le premier !
		cherrypy.session['mem_scroll'] = '0'
		# Affichage de la page de gestion des dossiers
		return self.affi_dossier()		
	
	# Fonction qui génère la page html contenant les dossiers
	@cherrypy.expose
	def affi_dossier(self):
		# Renvoi d'une page HTML, formatée avec le nom de la commission :
		# On génère les 4 parties de la page html
		self.header = self.genere_header()
		self.dossier = self.genere_dossier(cherrypy.session['droits'])
		self.liste = self.genere_liste()
		# On retourne cette page au navigateur
		return mep(self.header, self.dossier,self.liste)
		
	# Fonction appelée par l'appui sur "VALIDER" : valide les choix commission ou Admin
	@cherrypy.expose
	def traiter(self, **kwargs):
	# Cette méthode est appelée par le bouton valider de la page dossier...
	# **kwargs empaquette les arguments passés par le navigateur dans le dictionnaire kwargs..
		cand = self.cand_cour()
		num_doss = cherrypy.session['num_doss']
		# mise à jour dans les variables de session du dossier du candidat...
		if cherrypy.session['droits'] != "administrateur":
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
			xml.set_jury(cand,cherrypy.session['droits'])
			# 3/ "bouléen" traite : dossier traité
			xml.set_traite(cand)
			# 4/ motif
			xml.set_motifs(cand, kwargs['motif'])
			# On sélectionne le dossier suivant
			if num_doss < len(cherrypy.session['dossiers'])-1:
				cherrypy.session['num_doss'] = num_doss+1
		else: # traitement administrateur
			# Si droits admin, on ne prend pas en compte les corrections et motivations
			# À-t-il changé qqc ? Si oui, mise à jour
			if xml.get_clas_actu(cand)!=kwargs['clas_actu']:
				xml.set_clas_actu(cand,kwargs['clas_actu'])
			# semestres ?
			try: # kwargs ne contient 'sem_prem' que si la case est cochée !!
				if kwargs['sem_prem']=='on':
					xml.set_sem_prem(cand,'on')
			except:
				xml.set_sem_prem(cand,'off')
			try:
				if kwargs['sem_term']=='on':
					xml.set_sem_term(cand,'on')
			except:
				xml.set_sem_term(cand,'off')
			# Cas des notes
			matiere = {'M':'Mathématiques','P':'Physique/Chimie'}
			date = {'1':'trimestre 1','2':'trimestre 2','3':'trimestre 3'}
			classe = {'P':'Première','T':'Terminale'}
			for cl in classe:
				for mat in matiere:
					for da in date:
						key = cl + mat + da
						if xml.get_note(cand,classe[cl],matiere[mat],date[da])!=kwargs[key]:
							xml.set_note(cand,classe[cl],matiere[mat],date[da],kwargs[key])
			# CPES
			if 'cpes' in xml.get_clas_actu(cand).lower():
				if xml.get_CM1(cand,True)!=kwargs['CM1']:
					xml.set_CM1(cand, kwargs['CM1'])
				if xml.get_CP1(cand,True)!=kwargs['CP1']:
					xml.set_CP1(cand, kwargs['CP1'])
			# EAF écrit et oral...		
			if xml.get_ecrit_EAF(cand)!=kwargs['EAF_e']:
				xml.set_ecrit_EAF(cand,kwargs['EAF_e'])
			if xml.get_oral_EAF(cand)!=kwargs['EAF_o']:
				xml.set_oral_EAF(cand,kwargs['EAF_o'])	
			# On (re)calcule le score brut !
			xml.calcul_scoreb(cand)
			xml.is_complet(cand) # mise à jour de l'état "dossier complet"
		## Et on sauvegarde immédiatement tout cela...
		self.sauvegarder()
		# Et on retourne au traitement...
		return self.affi_dossier()
		
	# On change de candidat après un clic dans la liste : c'est ICI !
	@cherrypy.expose
	def click_list(self,**kwargs): ## fonction appelée lors d'un click dans la liste de dossiers
		cherrypy.session["mem_scroll"] = kwargs['scroll_mem']
		txt = kwargs['num'] # on récupère l'argument num
		num_doss = int(txt[:3])-1 # on en extrait le numéro de dossier  (3 premiers caractères)
		cherrypy.session["num_doss"] = num_doss
		return self.affi_dossier()
	
	# Renvoie le candidat courant (lecture des cookies de session)
	def cand_cour(self):
		num_doss = cherrypy.session["num_doss"]
		return cherrypy.session["dossiers"][num_doss] # un élément etree
	
	# Renvoie le dictionnaire contenant les infos du dossier en cours
	def genere_dict(self, cand, droits):
		data = {}
		data.update({'Nom':xml.get_nom(cand)+', '+xml.get_prenom(cand)})
		data.update({'naiss':xml.get_naiss(cand)})
		data.update({'etab':xml.get_etab(cand)})
		txt = '[{}]-{}'.format(xml.get_id(cand),xml.get_INE(cand))
		data.update({'id':txt})
		data.update({'ref_fich':'docs_candidats/{}/docs_{}'.format(cherrypy.session["filiere"],xml.get_id(cand))})
		if droits =='administrateur':
			clas_inp = '<input type="text" id="clas_actu" name = "clas_actu" size = "10" value={}>'\
				.format(xml.get_clas_actu(cand))
			data.update({'clas_actu':clas_inp})
		else:
			data.update({'clas_actu':xml.get_clas_actu(cand)})
		# Cases à cocher semestres
		visib = 'disabled ' # pour les cases à cocher
		if droits == "administrateur":
			visib = ' '
		txt = visib
		if xml.get_sem_prem(cand)=='on': txt = 'checked'
		data.update({'sem_prem':txt})
		txt = visib
		if xml.get_sem_term(cand)=='on': txt = 'checked'
		data.update({'sem_term':txt})
		# Notes
		matiere = {'M':'Mathématiques','P':'Physique/Chimie'}
		date = {'1':'trimestre 1','2':'trimestre 2','3':'trimestre 3'}
		classe = {'P':'Première','T':'Terminale'}
		for cl in classe:
			for mat in matiere:
				for da in date:
					key = cl + mat + da
					note = '{}'.format(xml.get_note(cand, classe[cl],\
							matiere[mat],date[da]))
					note_inp = '<input type = "text" class = "notes grossi"\
						 id = "{}" name = {} value = "{}">'.format(key,key,note)
					if droits == 'administrateur':
						data.update({key:note_inp})
					else:
						data.update({key:note})
		# CPES
		cpes = False
		if 'cpes' in xml.get_clas_actu(cand).lower():
			cpes = True
		if droits == 'administrateur':
			note_CM1 = '<input type = "text" class = "notes grossi"\
					 id = "CM1" name = "CM1" value = "{}">'.format(xml.get_CM1(cand,cpes))
			data.update({'CM1':note_CM1})
			note_CP1 = '<input type = "text" class = "notes grossi"\
					 id = "CP1" name = "CP1" value = "{}">'.format(xml.get_CP1(cand,cpes))
			data.update({'CP1':note_CP1})
		else:
			data.update({'CM1':'{}'.format(xml.get_CM1(cand,cpes))})
			data.update({'CP1':'{}'.format(xml.get_CP1(cand,cpes))})
		# EAF
		if droits == 'administrateur':
			note_eaf_e = '<input type = "text" class = "notes grossi"\
						 id = "EAF_e" name = "EAF_e" value = "{}">'.format(xml.get_ecrit_EAF(cand))
			data.update({'EAF_e':note_eaf_e})
			note_eaf_o = '<input type = "text" class = "notes grossi"\
						 id = "EAF_o" name = "EAF_o"value = "{}">'.format(xml.get_oral_EAF(cand))
			data.update({'EAF_o':note_eaf_o})
		else:
			data.update({'EAF_e':xml.get_ecrit_EAF(cand)})
			data.update({'EAF_o':xml.get_oral_EAF(cand)})		
		# Suite
		data.update({'scoreb':xml.get_scoreb(cand)})
		data.update({'scoref':xml.get_scoref(cand)})
		data.update({'cand':xml.get_candidatures_impr(cand)})
		return data
	
	# Génère l'entête de page HTML
	def genere_header(self): # comme son nom l'indique, cette fonction génère une chaine 
		qui = cherrypy.session.get('droits','') # de caractères qui est le code html du header...
		sous_titre = ''
		if qui !='': # sur la page d'authentification, pas de sous-titre...
			sous_titre = ' - Accès {}.'.format(qui)
		return '<h1 align="center">EPA - Recrutement CPGE/CPES {}</h1>'.format(sous_titre)
	
	# Génère la partie dossier de la page HTML
	def genere_dossier(self, droits): # fonction générant le code html du dossier
		# Candidat courant ?
		cand = self.cand_cour()
		# récupération correction
		correc = str(xml.get_correc(cand))
		ncval = ''
		if correc == 'NC': 
			correc = 0
			ncval = 'NC'
		# Construction de la barre de correction :
		barre = '<tr><td width = "2.5%"></td><td>'
		barre += '<input type = "range" class = "range" min="-3" \
				max = "3" step = ".25" name = "correc" id = "correc" \
				onchange="javascript:maj_note();" \
				onmousemove="javascript:maj_note();" \
				onclick="click_range();" \
				value = "{}">'.format(correc)
		barre += '</td><td width = "2.5%"></td></tr>' # fin de la ligne range
		txt = '' # on construit maintenant la liste des valeurs...
		for i in range(0,len(corrections)+1):
			if (i % 2 == 0):
				txt += '<td width = "7%">{:+3.1f}</td>'.format(corrections[i])
		barre += '<tr><td align = "center" colspan = "3"><table width = "100%">\
				<tr class = "correc_notimpr">{}</tr></table>'.format(txt)
		barre += '<span class = "correc_impr">'+xml.get_jury(cand)+' : {:+.2f}'.format(float(correc))+'</span>'
		barre += '</td></tr>'
		# input hidden nc
		nc = '<input type="hidden" id = "nc"  name = "nc" value = "{}">'.format(ncval)
		# Construction de la chaine motifs. Idem, on affecte checked aux bonnes cases...
		motifs = ''
		for i in range(0,len(motiv)):
			key = 'mot_'+str(i)
			motifs += '<td align = "left"><input type="button" name="'+key
			motifs += '" id="'+key+'" onclick="javascript:maj_motif(this.id)"'
			#if doss[key] == 'on':
			#	motifs += ' checked'
			motifs += ' class = "motif" value ="'+ motiv[key]+'"></td></tr>'
		# le dernier motif : autre ... 
		motifs += '<tr><td align = "left">'
		motifs += '<input type="text" class = "txt_motifs" name="motif" id = "motif" value= "'
		try:
			motifs += xml.get_motifs(cand)+'">'
		except:
			motifs += '">'
		motifs += "</td>"
	
		# On met tout ça dans un dico data pour passage en argument à page_dossier
		data = self.genere_dict(cand, droits) 
		data.update({'barre':barre})
		data.update({'nc':nc})
		data.update({'motifs':motifs})
		return html["page_dossier"].format(**data)
		
	# Génère la partie liste de la page HTML
	def genere_liste(self):
		liste = cherrypy.session['dossiers']
		num_doss = cherrypy.session['num_doss']
		# Construction de la chaine lis : code html de la liste des dossiers.
		lis = '<form id = "form_liste" action = "click_list" method=POST>'
		lis += '<input type="hidden" name = "scroll_mem" value = "'
		lis += cherrypy.session['mem_scroll']+'">' # mémo du scroll
		for i in range(0,len(liste)):
			lis += '<input type = "submit" name="num" '
			clas = 'doss'
			if i == num_doss: # affecte la class css "doss_courant" au dossier  courant
					clas += ' doss_courant'
			if xml.get_traite(liste[i]) != '':
					clas += ' doss_traite' # affecte la classe css "doss_traite" aux ...
			if cherrypy.session['droits'] == "administrateur":
				if xml.get_complet(liste[i])=='non':	# Dossier incomplet (seulement admin ?)
					clas += ' doss_incomplet'
			lis += 'class = "{}"'.format(clas)
			nom = xml.get_nom(liste[i])+', '+xml.get_prenom(liste[i])
			txt = '{:3d}) {: <28}{}'.format(i+1,nom[:27],xml.get_candidatures(liste[i]))
			lis += ' value="'+txt+'"></input><br>'
		# txt est le txt que contient le bouton. Attention, ses 3 premiers
		# caractères doivent être le numéro du dossier dans la liste des
		# dossiers (cherrypy.session['dossiers'])...
		lis += '-'*7+' fin de liste '+'-'*7
		lis = lis + '</form>'	
		return lis

	# Lit le fichier XML choisi et vérifie la complétude des dossiers
	def lire_fichier(self):
	# Les données candidats sont récupérées depuis un fichier xml.
		fichier = cherrypy.session["fichier"]
		tree = etree.parse(fichier)
		for cand in tree.getroot():
			xml.is_complet(cand) # on renseigne le noeud complet (oui/non)
		return tree.getroot()
			
	# Sauvegarde le fichier traité (appelé par la fonction traiter)
	def sauvegarder(self):
	# fonction qui met à jour (par écrasement) le fichier xml contenant les dossiers
		fichier = cherrypy.session["fichier"]
		donnees = cherrypy.session["dossiers"]
		with open(fichier, 'wb') as fich:
			fich.write(etree.tostring(donnees, pretty_print=True, encoding='utf-8'))
		return None
 	
 	# Générer les fichier epa_comm_mpsi1.xml jusqu'à epa_comm_cpes3.xml
	@cherrypy.expose
	def genere_fichiers_comm(self):
		# Récupération des fichiers admin
		chemin = "./data/epa_admin_*.xml"
		list_fich = glob.glob(chemin)
 		# Pour chaque fichier "epa_admin_*.xml"
		for fich in list_fich:
			doss = etree.parse(fich).getroot()
			# Tout d'abord, calculer le score brut de chaque candidat 
			for cand in doss:
				xml.calcul_scoreb(cand)
			# Classement par scoreb décroissant
			doss[:] = sorted(doss, key = lambda cand: -float(cand.xpath('diagnostic/score')[0].text.replace(',','.')))
			# Récupération de la filière 
			fil = parse('./data/epa_admin_{}.xml',fich)
			nbjury = int(nb_jury[fil[0].lower()])
			# Découpage en n listes de dossiers
			for j in range(0,nbjury):
				copie = copy.deepcopy(doss) # sinon, les candidats sont retirés de doss
				dossier = []				# à chaque append vers dossier (???!!!)
				[dossier.append(copie[i]) for i in range(0,len(copie)) if i%nbjury == j]
				# Sauvegarde
				res = etree.Element('candidats')
				[res.append(cand) for cand in dossier]
				nom = './data/epa_comm_{}{}.xml'.format(fil[0],j+1)
				with open(nom, 'wb') as fichier:
					fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
			
		# Enfin, on retourne à la page admin...
		data = {'acces':'Accès administrateur'}
		return self.identification(**data)

	# Convertit une date de naissance en un nombre pour le classement
	def convert(self, naiss):
		dic = parse('{j:d}/{m:d}/{a:d}',naiss)
		return dic['a']*10**4+dic['m']*10**2+dic['j']
	
	# Récolter les fichiers après la commission
	@cherrypy.expose
	def genere_fichiers_class(self):
		# Pour chaque commission
		for comm in filieres:
			chemin = './data/epa_comm_{}*.xml'.format(comm.upper())
			list_fich = glob.glob(chemin)
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
				# Sauvegarde du fichier classé ??
				#with open(fich, 'wb') as fichier:
				#	fichier.write(etree.tostring(doss, pretty_print=True, encoding='utf-8'))
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
				nom = './data/epa_class_{}.xml'.format(comm.upper())
				with open(nom, 'wb') as fichier:
					fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
				
		# Retour menu admin
		data = {'acces':'Accès administrateur'}
		return self.identification(**data)
	
	# Générer la page html pour impression des fiches commission
	@cherrypy.expose
	def page_impression(self, **kwargs):
		cherrypy.session["fichier"] = kwargs["fichier"]
		r = parse('{}class_{}.xml', kwargs["fichier"]) # récupère nom commission
		cherrypy.session["filiere"] = r[1].lower()
		cherrypy.session['dossiers'] = self.lire_fichier()
		doss = cherrypy.session['dossiers']
		txt = '<head><meta content="text/html; charset=utf-8" http-equiv="Content-Type">\
				<link rel="stylesheet" type="text/css" media="print" \
				href="/utils/style_impr.css"><link rel="stylesheet" type="text/css" \
				media="screen" \
				href="/utils/style_html_impr.css">'
		txt += '<body width = "50vw" onload = "window.print();">'
		txt += '<form action="/retour_menu_admin" method = POST>\
				<div id = "gros_bout_div"><input type = "submit" \
				class ="gros_bout" value = "RETOUR" \
				style = "display:{visibilite}"></div></form>'
		for cand in doss:
			if xml.get_scoref(cand) != 'NC':
				txt += '<h1 align="center" class = "titre">EPA - Recrutement CPGE/CPES - {}</h1></head>'.format(r[1].upper())
				if xml.get_rang(cand) == 'NC':# Ce test est un résidu d'une époque ou on générait une fiche même si le candidat n'était pas classé !
					txt += '<div class = encadre>Candidat non classé</div>'
				else:
					 txt += '<div class = encadre>Candidat classé : {}</div>'.format(xml.get_rang(cand))
				cherrypy.session['num_doss'] = doss.index(cand)
				txt += self.genere_dossier("commission")
				txt += '<div style = "page-break-after: always;"></div>'
		txt += '</body>'
		txt += '<script type="text/javascript">'
		txt += 'document.forms["formulaire"]["motifs"].disabled = true;</script>'
		
		return txt
	
	# Générer les tableaux .csv bilans de la commission
	@cherrypy.expose
	def tableaux_bilan(self, **kwargs):
		# Un peu de ménage...
		dest = './tableaux'
		try:
			self.efface_dest(dest) # on efface toute l'arborescence fille de chemin
		except: # dest n'existe pas !
			os.mkdir(dest) # on le créé...
		# Création du fichier d'aide
		with open(dest+'/aide.txt', 'w') as fi:
			txt = 'En cas de difficultés à ouvrir les .csv avec EXCEL,\n'
			txt += 'il est conseillé d\'utiliser la fonction fichier-->importer'
			fi.write(txt)
		fi.close()
		# Récupération des fichiers
		chemin = './data/epa_class_*.xml'
		list_fich = glob.glob(chemin)
		# Pour chaque filière :
		for fich in list_fich:
			# lecture fichier
			doss = etree.parse(fich).getroot()
			# 1er tableau : liste ordonnée des candidats retenus, pour Jeanne
			nom = './tableaux/'
			nom += parse('./data/epa_class_{}.xml',fich)[0]
			nom += '_retenus.csv'
			c = csv.writer(open(nom,'w'))
			entetes = ['Rang','Nom','Prénom','Date de naissance','score brut',\
						'correction','score final','jury','Observations']
			c.writerow(entetes)
			for cand in doss:
				if xml.get_scoref(cand) != 'NC': # seulement les classés !!
					data = [xml.get_rang(cand)]
					data.append(xml.get_nom(cand))
					data.append(xml.get_prenom(cand))
					data.append(xml.get_naiss(cand))
					data.append(xml.get_scoreb(cand))
					data.append(xml.get_correc(cand))
					data.append(xml.get_scoref(cand))
					data.append(xml.get_jury(cand))
					data.append(xml.get_motifs(cand))
					c.writerow(data)
			# 2e tableau : liste ordonnée des candidats retenus, pour Bureau des élèves
			# Le même que pour Jeanne, mais sans les notes...
			nom = './tableaux/'
			nom += parse('./data/epa_class_{}.xml',fich)[0]
			nom += '_retenus(sans_note).csv'
			c = csv.writer(open(nom,'w'))
			entetes = ['Rang','Nom','Prénom','Date de naissance']
			c.writerow(entetes)
			for cand in doss:
				if xml.get_scoref(cand) != 'NC': # seulement les classés !!
					data = [xml.get_rang(cand)]
					data.append(xml.get_nom(cand))
					data.append(xml.get_prenom(cand))
					data.append(xml.get_naiss(cand))
					c.writerow(data)
			# 3e tableau : Liste alphabétique de tous les candidats avec le numéro dans le classement,
			# toutes les notes et qq infos administratives
			# Fichier destination
			nom = './tableaux/'
			nom += parse('./data/epa_class_{}.xml',fich)[0]
			nom += '_alphabetique.csv'
			c = csv.writer(open(nom,'w'))
			entetes = ['Rang','Candidatures','Nom','Prénom','Date de naissance',\
					'Sexe','Nationalité','id_apb','Boursier','Classe actuelle',\
					'Etablissement','Commune Etablissement']
			# entêtes notes...
			matiere = {'M':'Mathématiques','P':'Physique/Chimie'}
			date = {'1':'trimestre 1','2':'trimestre 2','3':'trimestre 3'}
			classe = {'P':'Première','T':'Terminale'}
			for cl in classe:
				for da in date:
					for mat in matiere:
						key = cl + mat + da
						entetes.append(key)
			entetes.append('F_écrit')
			entetes.append('F_oral')
			entetes.append('CPES_math')
			entetes.append('CPES_phys')
			# la suite
			entetes.append('score brut')
			entetes.append('correction')
			entetes.append('score final')
			entetes.append('jury')
			entetes.append('Observations')
			c.writerow(entetes)
			# Classement alphabétique
			doss[:] = sorted(doss, key = lambda cand: xml.get_nom(cand))
			# Remplissage du fichier dest
			for cand in doss:
				data = [xml.get_rang(cand)]
				data.append(xml.get_candidatures(cand))
				data.append(xml.get_nom(cand))
				data.append(xml.get_prenom(cand))
				data.append(xml.get_naiss(cand))
				data.append(xml.get_sexe(cand))
				data.append(xml.get_nation(cand))
				data.append(xml.get_id(cand))
				data.append(xml.get_boursier(cand))
				data.append(xml.get_clas_actu(cand))
				data.append(xml.get_etab(cand))
				data.append(xml.get_commune_etab(cand))
				# Les notes...
				for cl in classe:
					for da in date:
						for mat in matiere:
							key = cl + mat + da
							note = '{}'.format(xml.get_note(cand, classe[cl],\
								matiere[mat],date[da]))
							data.append(note)
				data.append(xml.get_ecrit_EAF(cand))
				data.append(xml.get_oral_EAF(cand))
				cpes = 'cpes' in xml.get_clas_actu(cand).lower()
				data.append(xml.get_CM1(cand,cpes))
				data.append(xml.get_CP1(cand,cpes))
				# La suite
				data.append(xml.get_scoreb(cand))
				data.append(xml.get_correc(cand))
				data.append(xml.get_scoref(cand))
				data.append(xml.get_jury(cand))
				data.append(xml.get_motifs(cand))
				c.writerow(data)
		# Retour au menu
		cherrypy.session['tableaux'] = 'ok' # Ça c'est pour un message ok !
		data = {'acces':'Accès administrateur'}
		return self.identification(**data)

# === PROGRAMME PRINCIPAL ===
# Chargement des corrections de la commission
corrections = charger_correc()
# Chargement des motivations de la commission
motiv = charger_motifs()
# Chargement des "patrons" de pages web dans un dictionnaire global :
html = chargerPatronsHTML() # html est un dictionnaire contenant les patrons HTML
# Reconfiguration et démarrage du serveur web :
cherrypy.config.update({"tools.staticdir.root":os.getcwd()})
cherrypy.quickstart(Commission(),'/', config ="utils/config.conf")
