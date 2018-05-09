#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os, PyPDF2
from parse import parse
from parse import compile
from utils.parametres import filieres


## Méthodes de pré-traitement et de post-traitement
# accompagnées de fonctions de conversion utiles à la classe Fichier
def isnote(note):
    """ Teste si 'note' est bien un réel compris entre 0 et 20 """
    bool = True
    try:
        vers_num(note)
    except:
        bool = False
    return bool and vers_num(note)>=0 and vers_num(note)<=20

def vers_num(str):
    return float(str.replace(',','.'))

def vers_str(num):
    """ Convertit un nombre en une chaîne formatée à 2 décimales """
    return '{:5.2f}'.format(num).replace('.',',')

def not_note(note):
    """ si note n'est pas une note, renvoie '-' """
    if not isnote(note):
        note = '-'
    return note

def convert(str):
    """ formate la chaine 'str' contenant un nombre.
    Intérêt seulement esthétique dans la page web """
    return vers_str(vers_num(str))

def formate_candid(cc):
    """ transforme un mot binaire contenant les candidatures
    en une chaîne 'MP-' ou 'M-C', etc. """
    bina = bin(cc)[2:] # chaine exprimant cc en binaire (on enlève les 2 premiers caract. : '0b')
    while len(bina) < len(filieres):
        bina = '0{}'.format(bina) # on complète pour qu'il y ait le bon nb de digits.
    cc = ''
    for i in range(len(filieres)):
        if bina[-1-i] == '1':
            cc += filieres[i][0].upper()
        else:
            cc += '-'
    return cc

def formate_impr_candid(cc):
    """ Formate le contenu du noeud 'candidatures multiples' en vue de l'impression """
    return '-'.join(fil.upper() for fil in filieres if cc[filieres.index(fil)]!='-')

def formate_jury(jury):
    """ formate le contenu du champ 'jury' (pour affichage dans les tableaux) """
    if not('Admin' in jury):
        jury = parse('Jury {}', jury)[0]
    return jury

def num_score(sc):
    """ Pour les tris, convertit un score 'NC' en la valeur 0 et renvoie un float"""
    if sc == 'NC': sc = '0'
    return vers_num(sc)

## Fonction de découpage du fichier pdf
def decoup(sourc, dest):
    """ découpage du fichier pdf en autant de fichiers que de candidats """
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

############## Manipulation de répertoires
def efface_dest(chem):
    """ Supprime le dossier pointé par le chemin chem """
    for filename in os.listdir(chem):
        fich = os.path.join(chem, filename)
        if os.path.isdir(fich):
            efface_dest(fich) # appel récursif pour les sous-dossiers
        else:
            os.remove(fich) # on efface les fichiers
    os.rmdir(chem) # suppression du dossier vide

def restaure_virginite(chem): #  amélioration : shutil a une fonction qui supprime un répertoire non vide
    """ Créé le répertoire pointé par chem ou le vide s'il existe
    En gros, redonne une complète virginité à ce répertoire """
    if os.path.exists(chem):
        efface_dest(chem) # on efface chem (s'il existe)
    os.mkdir(chem) # on le (re)-créé

