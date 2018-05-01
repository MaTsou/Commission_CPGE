#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os, sys, glob, pickle, PyPDF2
from parse import parse
from parse import compile
from lxml import etree
import utils.interface_xml as xml
from utils.parametres import filieres
# contient différentes fonctions utiles


############## Manipulation de répertoires
def efface_dest(chem):
    # Supprime le dossier pointé par le chemin chem
    for filename in os.listdir(chem):
        fich = os.path.join(chem, filename)
        if os.path.isdir(fich):
            efface_dest(fich) # appel récursif pour les sous-dossiers
        else:
            os.remove(fich) # on efface les fichiers
    os.rmdir(chem) # suppression du dossier vide

def restaure_virginite(chem): #  amélioration : shutil a une fonction qui supprime un répertoire non vide
    # Créé le répertoire pointé par chem ou le vide s'il existe
    # En gros, redonne une complète virginité à ce répertoire
    efface_dest(chem) # on efface chem (s'il existe)
    os.mkdir(chem) # on le (re)-créé

############## Découpage du fichier PDF (dossiers candidats)
def decoup(sourc, dest):
	"sourc: fichier source"
	"dest: dossier destination"
	# précompilation de la requête pour gagner en vitesse
	regex = compile('{}Dossier n°{id:d}{}Page {page:d}')
	pdfFileObj = open(sourc, 'rb')
	pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
	page_deb = -1
	id_cand = -1
        # pour le candidat -1, au lieu de faire un cas particulier
	pdfWriter = PyPDF2.PdfFileWriter()
	for page in range(pdfReader.numPages):
                # récupération de la page courante
		pageObj = pdfReader.getPage(page)
                # puis de son texte brut
		txt = pageObj.extractText()
                # et enfin, numéro de dossier et page
		res = regex.parse(txt)
		if res or page == pdfReader.numPages-1:
                        # est-ce un changement de candidat?
			if (id_cand != res['id']
                            or page == pdfReader.numPages-1):
				nom = os.path.join (dest, 'docs_{}.pdf'.format(id_cand))
				pdfOutputFile = open(nom, 'wb')
                                # sinon il en manque un bout
				if page == pdfReader.numPages-1:
                                        pdfWriter.addPage(pageObj)
                                # écrasement de tout fichier existant!!
				pdfWriter.write(pdfOutputFile)
				pdfOutputFile.close()
				# réinitialisations
				pdfWriter = PyPDF2.PdfFileWriter()
				id_cand = res['id']
			pdfWriter.addPage(pageObj)
	os.remove(os.path.join(dest, 'docs_-1.pdf'))

############## Création des statistiques (nb candidatures par filière).
def trouve(iden, num_fil, cc, root, fil):
    # Sous-fonction de la fonction stat...
    # Sert à construire le binaire '001', '101', etc, indiquant les candidatures multiples..
    if num_fil < len(root)-1:  
        cand = root[num_fil+1].xpath('./candidat/id_apb[text()={}]'.format(iden))
        if cand:
            cc |= 2**(filieres.index(fil[num_fil + 1].lower())) # un OU évite les surcomptes !
        cc = trouve(iden, num_fil + 1, cc, root, fil)
        if cand: xml.set_candidatures(cand[0].getparent(), cc)
    return cc
        
def stat():
    # Effectue des statistiques sur les candidats
    list_fich = glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))
    parser = etree.XMLParser(remove_blank_text=True)
    root = [etree.parse(fich, parser).getroot() for fich in list_fich]
    fil = [parse(os.path.join(os.curdir, "data", "admin_{}.xml"), fich)[0] for fich in list_fich]

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
    deja_vu = [] # À TESTER PLUS TARD : UN 'SET' SERAIT SANS DOUTE PLUS ADAPTÉ (RAPIDITÉ)
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
                cc = trouve(iden, i, cc, root, fil)
                xml.set_candidatures(candi, cc) # on écrit le binaire obtenu dans le dossier candidat
                # Incrémentation des compteurs
                for j in range(2**len(filieres)):
                    xx = (cc == j)
                    yy = (cc != 2**index)
                    zz = (xml.get_motifs(candi) != '- Admin : Candidature non validée sur ParcoursSUP')
                    if (xx and yy and zz): #  seulement les multi-candidatures validées
                        candid[j] += 1
    # Sauvegarder
    for i in range(len(root)):
        with open(list_fich[i], 'wb') as fi:
            fi.write(etree.tostring(root[i], pretty_print=True, encoding='utf-8'))
    
    # Écrire le fichier stat
    with open(os.path.join(os.curdir, "data", "stat"), 'wb') as stat_fich:
        pickle.dump(candid, stat_fich)

#############################################
