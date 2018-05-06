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
# contient différentes fonctions utiles
 
############## Test is_complet dossier et calcul score brut
def is_complet(cand):
    # La synthèse (notes de 1e, Tle, bac français, etc.) est elle complète (sert à l'Admin)
    complet = True
    matiere = {'M':'Mathématiques','P':'Physique/Chimie'}
    # Notes de première
    date = {'1':'trimestre 1','2':'trimestre 2'}
    if get_sem_prem(cand) != 'on': # gestion des semestres
        date.update({'3':'trimestre 3'})
    classe = {'P':'Première'}
    for cl in classe:
            for mat in matiere:
                for da in date:
                    key = cl + mat + da
                    if get_note(cand, classe[cl],matiere[mat],date[da]) == '-':
                        complet = False
    # Notes de terminale
    if 'cpes' in get_clas_actu(cand).lower():
        date = {'1':'trimestre 1', '2':'trimestre 2'}
        add = '3' # à ajouter si le candidat n'est pas noté en semestres
    else:
        date = {'1':'trimestre 1'}
        add = '2' # à ajouter si le candidat n'est pas noté en semestres
    if get_sem_term(cand) != 'on': # gestion des semestres
        date.update({'{}'.format(add):'trimestre {}'.format(add)})
    classe ={'T':'Terminale'} 
    for cl in classe:
            for mat in matiere:
                for da in date:
                    key = cl + mat + da
                    if get_note(cand, classe[cl],matiere[mat],date[da]) == '-':
                        complet = False
    # Notes de CPES
    if 'cpes' in get_clas_actu(cand).lower():
        if get_CM1(cand, True) == '-':
            complet = False
        if get_CP1(cand, True) == '-':
            complet = False
    # EAF
    if get_ecrit_EAF(cand) == '-':
        complet = False
    if get_oral_EAF(cand) == '-':
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
                key = '{}_Première_{}'.format(mat, t)
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
                    key = '{}_Terminale_{}'.format(mat, t)
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
                    key = '{}_Terminale_trimestre 1'.format(mat)
                    note = xml.get(cand, key)
                    if note != '-':
                        tot += xml.vers_num(note)
                        nb += 1
            else:
                trim = ['trimestre 1','trimestre 2']
                for t in trim:
                    for mat in matiere:
                        key = '{}_Terminale_{}'.format(mat, t)
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
def stat():
    """ Effectue des statistiques sur les candidats"""
    list_fich = [Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))]
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
        # 1er tableau : liste ordonnée des candidats retenus, pour l'admin
        nom = os.path.join(os.curdir, "tableaux", "") # chaîne vide pour avoir / à la fin du chemin...
        nom += fich.filiere()
        nom += '_retenus.csv'
        c = csv.writer(open(nom, 'w'))
        entetes = ['Rang brut', 'Rang final', 'Nom', 'Prénom', 'Date de naissance', 'score brut', 'correction', 
        'score final', 'jury', 'Observations']
        c.writerow(entetes)
        for cand in fich:
            a = (xml.get(cand, 'Score final') != 'NC')
            b = not(a) or (int(xml.get(cand, 'Rang final')) <= int(nb_classes[fich.filiere().lower()]))
            if a and b: # seulement les classés dont le rang est inférieur à la limite fixée
                data = [fonction(cand) for fonction in [xml.get_rang_brut, xml.get_rang_final, xml.get_nom, 
                xml.get_prenom, xml.get_naiss, xml.get_scoreb, xml.get_correc, xml.get_scoref, xml.get_jury, 
                xml.get_motifs]]
                c.writerow(data)
        # 2e tableau : liste ordonnée des candidats retenus, pour Bureau des élèves
        # Le même que pour l'admin, mais sans les notes, ni les rangs bruts...
        nom = os.path.join(os.curdir, "tableaux", "") # chaîne vide pour avoir / à la fin du chemin..
        nom += fich.filiere()
        nom += '_retenus(sans_note).csv'
        c = csv.writer(open(nom, 'w'))
        entetes = ['Rang final', 'Nom', 'Prénom', 'Date de naissance']
        c.writerow(entetes)
        for cand in fich:
            a = (xml.get(cand, 'Score final') != 'NC')
            b = not(a) or (int(xml.get(cand, 'Rang final')) <= int(nb_classes[fich.filiere().lower()]))
            if a and b: # seulement les classés dont le rang est inférieur à la limite fixée
                data = [fonction(cand) for fonction in [xml.get_rang_final , xml.get_nom, 
                xml.get_prenom, xml.get_naiss]]
                c.writerow(data)
        # 3e tableau : Liste alphabétique de tous les candidats avec le numéro dans le classement,
        # toutes les notes et qq infos administratives
        # Fichier destination
        nom = os.path.join(os.curdir, "tableaux", "") # chaîne vide pour avoir / à la fin du chemin...
        nom += fich.filiere()
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
        # Remplissage du fichier dest dans l'ordre alphabétique
        for cand in fich.ordonne('alpha'):
            data = [xml.get(cand, 'Rang brut'), xml.get(cand, 'Rang final'), xml.get(cand, 'Candidatures')]
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
