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
    "Convertit si possible une chaîne contenant un nombre à virgule en flottant"
    try:
        res = float(string.replace(',','.'))
    except ValueError:
        res = string
    return res

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

def normalize_mark(note):
    """ si note n'est pas une note valide, renvoie '-' """
    num = str_to_num(note)
    if type(num) != float or (not 0 <= num <= 20):
        note = '-'
    return note

def format_rank(rg):
    """ Renvoie l'entier rang ou la chaîne 'NC' selon le cas """
    try:
        rank = int(rg)
    except:
        rank = rg
    return rank
 
def format_candidatures(candidatures):
    """transforme un mot binaire contenant les candidatures en une chaîne
    'MP-' ou 'M-C', etc."""

    # chaine exprimant 'candidatures' en binaire
    # (on enlève les 2 premiers caract. : '0b')
    bina = bin(candidatures)[2:]
    while len(bina) < len(filieres):
        bina = f"0{bina}" # on complète pour qu'il y ait le bon nb de digits.
    res = ''
    for i, filiere in enumerate(filieres):
        if bina[-1-i] == '1':
            res += filiere[0].upper()
        else:
            res += '-'
    return res

def format_candidatures_impr(candidatures):
    """ Formate le contenu du noeud 'candidatures multiples' en vue de l'impression """
    if len(candidatures) != len(filieres):
        return ''
    return '-'.join(fil.upper() for fil in filieres if candidatures[filieres.index(fil)]!='-')

def format_jury(jury):
    """ formate le contenu du champ 'jury' (pour affichage dans les tableaux) """
    if 'Jury' in jury:
        jury = parse('Jury {}', jury)[0]
    return jury

## Fonction de découpage du fichier pdf
def decoup(src, dest):
    """découpage du fichier pdf en autant de fichiers que de candidats
    src: nom du fichier source
    dest: nom du dossier de destination"""

    # précompilation de la requête pour gagner en vitesse
    regex = compile('{}Dossier n°{id:d}{}Page {page:d}')
    with open(src, 'rb') as file_obj:
        reader = PyPDF2.PdfFileReader(file_obj)
        id_cand = -1
        # pour le candidat -1, au lieu de faire un cas particulier
        writer = PyPDF2.PdfFileWriter()
        for page_num in range(reader.numPages):
            page = reader.getPage(page_num)
            txt = page.extractText()
            res = regex.parse(txt)
            if res or page_num == reader.numPages-1:
                # si c'est un changement de candidat ou la fin du fichier
                if (id_cand != res['id']
                    or page_num == reader.numPages-1):
                    nom = os.path.join(dest, f'docs_{id_cand}.pdf')
                    with open(nom, 'wb') as output_file:
                        # sinon il en manque un bout
                        if page_num == reader.numPages-1:
                            writer.addPage(page)
                        # écrasement de tout fichier existant!!
                        writer.write(output_file)
                        # réinitialisations
                        writer = PyPDF2.PdfFileWriter()
                        id_cand = res['id']
                writer.addPage(page)
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

############## manipulation des noms de fichiers xml
# dictionnaire encapsulant les choix de nommage
naming = {
        'admin' : 'admin',
        'jury' : 'jury',
        'classement_final' : 'class',
        }

pattern = os.path.join(os.curdir, "data", "{}_{}.xml")

def xml_to_division(file_name):
    """ Récupération du nom de filière dans un nom de fichier xml """
    return parse(pattern, file_name)[1]

def division_to_xml(key, cursus):
    """ Construction du nom de fichier xml à partir de la filière et d'une clé 
    du dictionnaire naming """
    return pattern.format(naming[key], cursus)
