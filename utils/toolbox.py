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
    try:
        res = float(string.replace(',','.'))
    except ValueError:
        res = -1 # va être vu comme erroné
    return res

def num_to_str(num):
    'Convertit un flottant en chaîne avec deux chiffres après la virgule'
    return f'{num:.2f}'.replace('.', ',')

def date_to_num(naissance):
    'Convertit une chaîne donnant une date de naissance en nombre'
    try:
        dico = parse('{jour:d}/{mois:d}/{annee:d}', naissance)
        res = dico['annee']*10000+dico['mois']*100+dico['jour']
    except KeyError:
        res = 0
    return res

## Méthodes de pré-traitement et de post-traitement utilisées dans les
## fonctions get et set de la classe Fichier.

def normalize_note(note):
    """ si note n'est pas une note valide, renvoie '-' """
    num = str_to_num(note)
    if not 0 <= num <= 20:
        note = '-'
    return note

def format_mark(string):
    'Convertit une chaîne en nombre puis à nouveau en chaîne - esthétique'
    return num_to_str(str_to_num(string))

def format_candidatures(candidatures):
    """transforme un mot binaire contenant les candidatures en une chaîne
    'MP-' ou 'M-C', etc."""

    # chaine exprimant 'candidatures' en binaire
    # (on enlève les 2 premiers caract. : '0b')
    bina = bin(candidatures)[2:]
    while len(bina) < len(filieres):
        bina = '0{}'.format(bina) # on complète pour qu'il y ait le bon nb de digits.
    res = ''
    for i, filiere in enumerate(filieres):
        if bina[-1-i] == '1':
            res += filiere[0].upper()
        else:
            res += '-'
    return res

def format_candidatures_impr(candidatures):
    """ Formate le contenu du noeud 'candidatures multiples' en vue de l'impression """
    return '-'.join(fil.upper() for fil in filieres if candidatures[filieres.index(fil)]!='-')

def format_jury(jury):
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
    file_obj = open(sourc, 'rb')
    reader = PyPDF2.PdfFileReader(file_obj)
    id_cand = -1
        # pour le candidat -1, au lieu de faire un cas particulier
    writer = PyPDF2.PdfFileWriter()
    for page in range(reader.numPages):
        # récupération de la page courante
        page_obj = reader.getPage(page)
        # puis de son texte brut
        txt = page_obj.extractText()
        # et enfin, numéro de dossier et page
        res = regex.parse(txt)
        if res or page == reader.numPages-1:
            # est-ce un changement de candidat?
            if (id_cand != res['id']
                    or page == reader.numPages-1):
                nom = os.path.join (dest, 'docs_{}.pdf'.format(id_cand))
                output_file = open(nom, 'wb')
                # sinon il en manque un bout
                if page == reader.numPages-1:
                    writer.addPage(page_obj)
                # écrasement de tout fichier existant!!
                writer.write(output_file)
                output_file.close()
                # réinitialisations
                writer = PyPDF2.PdfFileWriter()
                id_cand = res['id']
            writer.addPage(page_obj)
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
