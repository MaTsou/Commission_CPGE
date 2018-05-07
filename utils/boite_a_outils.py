#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os, glob, pickle, PyPDF2, csv, copy
from parse import parse
from parse import compile
from lxml import etree
import utils.interface_xml as xml
from utils.parametres import coef_cpes
from utils.parametres import coef_term
from utils.parametres import prop_ecrit_EAF 
from utils.parametres import prop_prem_trim
from utils.parametres import filieres
from utils.parametres import nb_classes
from utils.parametres import tableaux_candidats_classes
from utils.parametres import tableaux_tous_candidats
# contient différentes fonctions utiles
 
############## Test is_complet dossier et calcul score brut
def is_complet(cand):
    # La synthèse (notes de 1e, Tle, bac français, etc.) est elle complète (sert à l'Admin)
    # Construction de la liste des champs à vérifier
    champs = set([])
    matiere = ['Mathématiques', 'Physique/Chimie']
    # Première
    classe = 'Première'
    date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
    for mat in matiere:
        for da in date:
            champs.add('{} Première {}'.format(mat , da))
    # Terminale
    classe = 'Terminale'
    date = ['trimestre 1', 'trimestre 2']
    if 'cpes' in xml.get(cand, 'Classe actuelle').lower():
        date.append('trimestre 3')
    for mat in matiere:
        for da in date:
            champs.add('{} Terminale {}'.format(mat , da))
    # CPES
    if 'cpes' in xml.get(cand, 'Classe actuelle').lower():
        champs.add('Mathématiques CPES')
        champs.add('Physique/Chimie CPES')
    # EAF
    champs.add('Écrit EAF')
    champs.add('Oral EAF')
    # Test :
    complet = not(xml.get(cand, 'Classe actuelle') == '?') # une initialisation astucieuse..
    while (complet and len(champs) > 0):
        ch = champs.pop()
        if xml.get(cand, ch) == '-':
            complet = False
    return complet

def calcul_scoreb(cand):
    # Calcul du score brut
    # Si correc = 'NC', cela signifie que l'admin rejette le dossier : scoreb = 0
    scoreb = xml.vers_str(0) # valeur si correc = 'NC'
    if xml.get(cand, 'Correction') != 'NC':
        # Récupération des coef
        if 'cpes' in xml.get(cand, 'Classe actuelle').lower(): 
            coef = coef_cpes
        else:
            coef = coef_term
        # moyenne de première
        tot = 0
        nb = 0
        matiere = ['Mathématiques', 'Physique/Chimie']
        trim = ['trimestre 1','trimestre 2','trimestre 3']
        for t in trim:
            for mat in matiere:
                key = '{} Première {}'.format(mat, t)
                note = xml.get(cand, key)
                if note != '-':
                    tot += xml.vers_num(note)
                    nb += 1
        if nb > 0:
            moy_prem = tot/nb
        else:
            moy_prem = 0
        # moyenne de terminale
        tot = 0
        nb = 0
        if coef['cpes']: # candidat en cpes (poids uniforme)
            trim = ['trimestre 1','trimestre 2','trimestre 3']
            for t in trim:
                for mat in matiere:
                    key = '{} Terminale {}'.format(mat, t)
                    note = xml.get(cand, key)
                    if note != '-':
                        tot += xml.vers_num(note)
                        nb += 1
            if nb > 0:
                moy_term = tot/nb
            else:
                moy_term = 0
        else: # candidat en terminale : 45% 1er trimestre ; 55% 2e trimestre (config dans parametre.py)
            if xml.get(cand, 'sem_term') == 'on':
                for mat in matiere:
                    key = '{} Terminale trimestre 1'.format(mat)
                    note = xml.get(cand, key)
                    if note != '-':
                        tot += xml.vers_num(note)
                        nb += 1
            else:
                trim = ['trimestre 1','trimestre 2']
                for t in trim:
                    for mat in matiere:
                        key = '{} Terminale {}'.format(mat, t)
                        note = xml.get(cand, key)
                        if note != '-':
                            if '1' in t:
                                tot += xml.vers_num(note)*prop_prem_trim
                                nb += prop_prem_trim 
                            else:
                                tot+= xml.vers_num(note)*(1-prop_prem_trim)
                                nb += 1-prop_prem_trim
            if nb > 0:
                moy_term = tot/nb
            else:
                moy_term = 0
        # moyenne EAF : 2/3 pour l'écrit et 1/3 pour l'oral
        tot = 0
        nb = 0
        note = xml.get(cand, 'Écrit EAF')
        if note != '-':
            tot += xml.vers_num(note)*prop_ecrit_EAF
            nb += prop_ecrit_EAF
        note = xml.get(cand, 'Oral EAF')
        if note != '-':
            tot += xml.vers_num(note)*(1-prop_ecrit_EAF)
            nb += 1-prop_ecrit_EAF
        if nb > 0:
            moy_EAF = tot/nb
        else:
            moy_EAF = 0
        # éventuellement moyenne de CPES
        if coef['cpes']: # candidat en cpes
            tot = 0
            nb = 0
            keys = ['Mathématiques CPES', 'Physique/Chimie CPES']
            for key in keys:
                note = xml.get(cand, key)
                if note != '-':
                    tot += xml.vers_num(note)
                    nb += 1
            if nb > 0:
                moy_cpes = tot/nb
            else:
                moy_cpes = 0
        # score brut
        tot = moy_prem*coef['Première'] + moy_term*coef['Terminale'] + moy_EAF*coef['EAF']
        nb = coef['Première'] + coef['Terminale'] + coef['EAF']
        if coef['cpes']:
            tot += moy_cpes*coef['cpes']
            nb += coef['cpes']
        scoreb = xml.vers_str(tot/nb)
    xml.set(cand, 'Score brut', scoreb)
        
############## Trouver le rang d'un candidat dans une liste de dossiers, selon un critère donné
def rang(cand, dossiers, critere):
    rg = 1
    score_actu = xml.get(cand, critere)
    if dossiers:
        while (rg <= len(dossiers) and xml.get(dossiers[rg-1], critere) > score_actu):
            rg+= 1
    return rg

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
    if os.path.exists(chem):
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
def stat(list_fich):
    """ Effectue des statistiques sur les candidats"""
    # On ordonne selon l'ordre spécifié dans filieres (parametres.py)
    list_fich = sorted(list_fich, key = lambda f: filieres.index(f.filiere().lower()))
    # L'info de candidatures est stockée dans un nombre binaire où 1 bit 
    # correspond à 1 filière. Un dictionnaire 'candid' admet ces nombres binaires pour clés,
    # et les valeurs sont des nombres de candidats. 
    # candid = {'001' : 609, '011' : 245, ...} indique que 609 candidats ont demandé
    # le filière 1 et 245 ont demandé à la fois la filière 1 et la filière 2

    # Initialisation du dictionnaire stockant toutes les candidatures
    candid = {i : 0 for i in range(2**len(filieres))}

    # Recherche des candidatures # je suis très fier de cet algorithme !!
    # Construction des éléments de recherche
    l_dict = [ {xml.get(cand, 'Num ParcoursSup') : cand for cand in fich} for fich in list_fich ] # liste de dicos
    l_set = [ set(d.keys()) for d in l_dict ] # list d'ensembles (set())
    # Création des statistiques
    for (k,n) in enumerate(l_set):
        while len(n) > 0:
            a = n.pop()
            cc, liste = 2**k, [k]
            for i in range(k+1, len(list_fich)):
                if a in l_set[i]:
                    cc |= 2**i
                    l_set[i].remove(a)
                    liste.append(i)
            [xml.set(l_dict[j][a], 'Candidatures', cc) for j in liste]
            for j in liste:
                if not('non validée' in xml.get(l_dict[j][a], 'Motifs')):
                    candid[2**j]+= 1
            if len(liste) > 1:
                candid[cc] += 1
    # Sauvegarder
    [fich.sauvegarde() for fich in list_fich]
    
    # Écrire le fichier stat
    with open(os.path.join(os.curdir, "data", "stat"), 'wb') as stat_fich:
        pickle.dump(candid, stat_fich)

############## Générer les tableaux .csv bilans de la commission
def tableaux_bilan(list_fich):
    """ Cette fonction créé les tableaux dont a besoin l'admin pour la suite du recrutement"""
    # Un peu de ménage...
    dest = os.path.join(os.curdir, "tableaux")
    restaure_virginite(dest)
    # Pour chaque filière :
    for fich in list_fich:
        # Tableaux candidats classés
        for name in tableaux_candidats_classes.keys():
            # Création du fichier csv
            nom = os.path.join(os.curdir, "tableaux", "{}_{}.csv".format(fich.filiere(), name))
            c = csv.writer(open(nom, 'w'))
            entetes = tableaux_candidats_classes[name]
            c.writerow(entetes)
            for cand in fich:
                a = (xml.get(cand, 'Score final') != 'NC')
                b = not(a) or (int(xml.get(cand, 'Rang final')) <= int(nb_classes[fich.filiere().lower()]))
                if a and b: # seulement les classés dont le rang est inférieur à la limite fixée
                    data = [xml.get(cand, champ) for champ in entetes]
                    c.writerow(data)
        # Tableaux tous candidats
        for name in tableaux_tous_candidats:
            # Création du fichier csv
            nom = os.path.join(os.curdir, "tableaux", "{}_{}.csv".format(fich.filiere(), name))
            c = csv.writer(open(nom, 'w'))
            entetes = tableaux_tous_candidats[name]
            c.writerow(entetes)
            for cand in fich.ordonne('alpha'):
                data = [xml.get(cand, champ) for champ in entetes]
                c.writerow(data)
