#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os
from parse import parse
from parse import compile

import PyPDF2

from config import filieres

##
# Fonctions de conversion
##

def num_to_col(num):
    'Convertit un numéro de colonne vers son nom dans un tableur'
    res = ''
    while num > 0:
        mod = (num-1) % 26
        res = chr(65+mod) + res
        num = (num-mod) // 26
    return res

def str_to_num(string):
    "Convertit une chaîne contenant un nombre à virgule en flottant"
    return float(string.replace(',','.'))

def num_to_str(num):
    'Convertit un flottant en chaîne avec deux chiffres après la virgule'
    return f'{num:.2f}'.replace('.', ',')

def str_to_num_to_str(string):
    'Convertit une chaîne en nombre puis à nouveau en chaîne - esthétique'
    return num_to_str(str_to_num(string))

def date_to_num(naissance):
    'Convertit une chaîne donnant une date de naissance en nombre'
    try:
        dico = parse('{jour:d}/{mois:d}/{annee:d}', naissance)
        res = dico['annee']*10000+dico['mois']*100+dico['jour']
    except:
        res = 0
    return res

## Méthodes de pré-traitement et de post-traitement utilisées dans les
## fonctions get et set de la classe Fichier.

def is_note(note):
    """ Teste si 'note' est bien un réel compris entre 0 et 20 """
    res = False
    try:
        num = str_to_num(note)
        result = 0 <= num <= 20
    except:
        pass
    return res

def normalize_note(note):
    """ si note n'est pas une note valide, renvoie '-' """
    if not is_note(note):
        note = '-'
    return note

def formate_candid(cc):
    """ transforme un mot binaire contenant les candidatures
    en une chaîne 'MP-' ou 'M-C', etc. """
    bina = bin(cc)[2:] # chaine exprimant cc en binaire (on enlève les 2 premiers caract. : '0b')
    while len(bina) < len(filieres):
        bina = '0{}'.format(bina) # on complète pour qu'il y ait le bon nb de digits.
    cc = ''
    for i, filiere in enumerate(filieres):
        if bina[-1-i] == '1':
            cc += filiere[0].upper()
        else:
            cc += '-'
    return cc

def formate_impr_candid(cc):
    """ Formate le contenu du noeud 'candidatures multiples' en vue de l'impression """
    return '-'.join(fil.upper() for fil in filieres if cc[filieres.index(fil)]!='-')

def formate_jury(jury):
    """ formate le contenu du champ 'jury' (pour affichage dans les tableaux) """
    if 'Jury' in jury:
        jury = parse('Jury {}', jury)[0]
    return jury

## Fonction de découpage du fichier pdf
def decoup(sourc, dest):
    """découpage du fichier pdf en autant de fichiers que de candidats
    sourc: fichier source
    dest: dossier destination"""
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

def restaure_virginite(chem): #  amélioration : shutil a une fonction
                              #  qui supprime un répertoire non vide
    """ Créé le répertoire pointé par chem ou le vide s'il existe
    En gros, redonne une complète virginité à ce répertoire """
    if os.path.exists(chem):
        efface_dest(chem) # on efface chem (s'il existe)
    os.mkdir(chem) # on le (re)-créé
