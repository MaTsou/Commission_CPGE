#!/usr/bin/env python3
#-*- coding: utf-8 -*-

from lxml import etree
from parse import parse
from utils.parametres import coef_cpes
from utils.parametres import coef_term
from utils.parametres import prop_ecrit_EAF 
from utils.parametres import prop_prem_trim
from utils.parametres import filieres

## Variables globales
alfil = sorted(filieres) # filières dans l'ordre alphabétique (sert dans get_candidatures)

###################################
# Quelques fonctions de conversion
###################################
def isnote(note):
    # Teste si 'note' est bien un réel compris entre 0 et 20
    bool = True
    try:
        vers_num(note)
    except:
        bool = False
    return bool and vers_num(note)>=0 and vers_num(note)<=20

def convert(str):
    # Convertit la chaîne 'str' en le nombre quelle contient (en lien avec isnote)
    num = vers_num(str)
    return vers_str(num)

def vers_num(str):
    str = str.replace(',','.')
    return float(str)

def vers_str(num):
    # Convertit un nombre en une chaîne formatée à 2 décimales
    str = '{:5.2f}'.format(num)
    return str.replace('.',',')

###################################
# Accesseur et mutateur standardisés
# Tous fonctionnant selon le même modèle, c'est plus léger ainsi
###################################
def get(cand, query, default, num='False'):
    # lit le champ désigné par 'query' relatif au candidat 'cand'
    # num vaut 'True' si la valeur à retourner est numérique
    try:
        result = cand.xpath(query)[0].text
        if num: result = convert(result)
    except:
        result = default
    return result

def set(cand, query, value):
    # écrit le champ désigné par 'query' relatif au candidat 'cand'
    # si besoin, construit l'arborescence manquante dans le fichier xml
    # Cette reconstruction se fait de manière récursive en commançant
    # par l'extrémité (les feuilles !)...
    return none


###################################
# Les accesseurs et mutateurs appelés
###################################
def get_candidatures(cand, form = ''):
    # Lit le champ candidatures (MP- ou M-- ou etc.) du candidat cand
    query = 'diagnostic/candidatures'
    try:
        cc = cand.xpath(query)[0].text
        if form == 'ord': # on rétablit l'ordre des filières donné par la liste filieres (cf parametres.py)
            cc = ''.join(cc[alfil.index(fil)] for fil in filieres)
        if form == 'impr': # ordonnées et nom complet.
            cc = '-'.join(fil.upper() for fil in filieres if cc[alfil.index(fil)]!='-')
    except:
        cc = '???'
    return cc

def set_candidatures(cand, cc):
    query = 'diagnostic/candidatures'
    try:
        cand.xpath(query)[0].text = cc
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'candidatures')
        subel.text = cc
    
def get_note(cand, classe, matiere, date):
    query = 'bulletins/bulletin[classe = "'+classe+'"]/matières/'
    query += 'matière[intitulé ="'+matiere+'"][date="'+date+'"]/note'
    return get(cand, query, '-', 1)

def set_note(cand, classe, matiere, date, note):
    query = 'bulletins/bulletin[classe = "'+classe+'"]/matières/'
    query += 'matière[intitulé ="'+matiere+'"][date="'+date+'"]'
    if not isnote(note):
        note = '-'
    try:
        cand.xpath(query+'/note')[0].text = note
    except: # Chemin vers la note à créer...
        el = cand.xpath(query)[0]
        subel = etree.SubElement(el, 'note')
        subel.text = note
        
def get_ecrit_EAF(cand):
    return get(cand, 'synoptique/français.écrit', '-', 1)

def set_ecrit_EAF(cand, note):
    if not isnote(note):
        note = '-'
    try:
        cand.xpath('synoptique/français.écrit')[0].text = note
    except:
        el = cand.xpath('synoptique')[0]
        subel = etree.SubElement(el, 'français.écrit')
        subel.text = note

def get_oral_EAF(cand):
    return get(cand, 'synoptique/français.oral', '-', 1)

def set_oral_EAF(cand, note):
    if not isnote(note):
        note = '-'
    try:
        cand.xpath('synoptique/français.oral')[0].text = note
    except:
        el = cand.xpath('synoptique')[0]
        subel = etree.SubElement(el, 'français.oral')
        subel.text = note
    
def get_CM1(cand,cpes):
    if cpes:
        return get(cand, 'synoptique/matières/matière[intitulé = "Mathématiques"]/note', '-', 1)
    else:
        return '-'

def set_CM1(cand, note):
    query = 'synoptique/matières/matière[intitulé = "Mathématiques"]/note'
    if not isnote(note):
        note = '-'
    try:
        cand.xpath(query)[0].text = note
    except:
        el = cand.xpath('synoptique/matières/matière[intitulé = "Mathématiques"]')[0]
        subel = etree.SubElement(el,'note')
        subel.text = note

def get_CP1(cand,cpes):
    if cpes:
        return get(cand, 'synoptique/matières/matière[intitulé = "Physique/Chimie"]/note', '-', 1)
    else:
        return '-'

def set_CP1(cand, note):
    query = 'synoptique/matières/matière[intitulé = "Physique/Chimie"]/note'
    if not isnote(note):
        note = '-'
    try:
        cand.xpath(query)[0].text = note
    except:
        el = cand.xpath('synoptique/matières/matière[intitulé = "Physique/Chimie"]')[0]
        subel = etree.SubElement(el, 'note')
        subel.text = note

def get_sem_prem(cand):
    # Lit le booléen "bulletins en semestres en classe de première" ?
    return get(cand, 'diagnostic/sem_prem', 'off', 0)

def set_sem_prem(cand,bool):
    query = 'diagnostic/sem_prem'
    try:
        cand.xpath(query)[0].text = bool
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'sem_prem')
        subel.text = bool

def get_sem_term(cand):
    # Lit le booléen "bulletins en semestres en classe de terminale" ?
    return get(cand, 'diagnostic/sem_term', 'off', 0)

def set_sem_term(cand,bool):
    query = 'diagnostic/sem_term'
    try:
        cand.xpath(query)[0].text = bool
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'sem_term')
        subel.text = bool
    
def get_nom(cand):
    return cand.xpath('nom')[0].text

def get_prenom(cand):
    return cand.xpath('prénom')[0].text
    
def get_sexe(cand):
    return get(cand, 'sexe', '?', 0)

def get_scoreb(cand):
    # score brut
    return get(cand, 'diagnostic/score', '', 1)
    
def get_traite(cand):
    return get(cand, 'diagnostic/traite', '', 0)

def set_traite(cand):
    try:
        cand.xpath('diagnostic/traite')[0].text = 'DOSSIER TRAITÉ'
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'traite')
        subel.text = 'DOSSIER TRAITÉ'       

def get_correc(cand):
    # correction du jury
    return get(cand, 'diagnostic/correc', '0', 0)

def set_correc(cand, correc):
    try:
        cand.xpath('diagnostic/correc')[0].text = correc
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'correc')
        subel.text = correc

def get_scoref(cand):
    # score final
    return get(cand, 'diagnostic/score_final', get_scoreb(cand), 0)

def get_scoref_num(cand): # version numérique, pour le classement NC --> 0
    scoref = get_scoref(cand)
    if scoref == 'NC': scoref = '0'
    return scoref
    
def set_scoref(cand, scoref):
    try:
        cand.xpath('diagnostic/score_final')[0].text = scoref
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'score_final')
        subel.text = scoref
    
def get_motifs(cand):
    # Motivation du jury
    return get(cand, 'diagnostic/motifs', '', 0)

def set_motifs(cand, txt):
    try:
        cand.xpath('diagnostic/motifs')[0].text = txt
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'motifs')
        subel.text = txt
    
def set_jury(cand,txt):
    # Quel jury a traité ce candidat ?
    try:
        cand.xpath('diagnostic/jury')[0].text = txt
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'jury')
        subel.text = txt

def get_jury(cand):
    try:
        txt = cand.xpath('diagnostic/jury')[0].text
        txt = parse('Jury {}',txt)[0]
    except:
        txt = 'Auto'
    return txt

def get_id(cand):
    # Identifiant unique APB (ou parcours Sup)
    return cand.xpath('id_apb')[0].text

def get_INE(cand):
    return get(cand, 'INE', '?', 0)

def get_naiss(cand):
    return cand.xpath('naissance')[0].text

def get_clas_actu(cand):
    return get(cand, 'synoptique/classe', '?', 0)

def set_clas_actu(cand, classe):
    try:
        cand.xpath('synoptique/classe')[0].text = classe
    except:
        el = cand.xpath('synoptique')[0]
        subel = etree.SubElement(el, 'classe')
        subel.text = classe

def get_etab(cand):
    etab = get(cand, 'synoptique/établissement/nom', '?', 0)
    dep = get(cand, 'synoptique/établissement/département', '?', 0)
    pays = get(cand, 'synoptique/établissement/pays', '?', 0)
    return '{} ({}, {})'.format(etab, dep, pays)
    
def get_commune_etab(cand):
     return get(cand, 'synoptique/établissement/ville', '?', 0)

def get_nation(cand):
    return get(cand, 'nationalité', '?', 0)

def get_boursier(cand):
    bours = get(cand, 'boursier', '?', 0)
    certif = get(cand, 'boursier_certifie', '?', 0)
    txt = 'oui'
    if 'non boursier' in bours.lower():
        txt = 'non'
    else:
        if 'oui' in certif.lower(): txt+= ' certifié'
    return txt

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
    set_complet(cand,complet)

def set_complet(cand,complet):
    # booléen synthèse complète... (voir fonction iscomplet ci-dessus)
    if complet:
        complet = 'oui'
    else: 
        complet = 'non'
    try:
        cand.xpath('diagnostic/complet')[0].text = complet
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'complet')
        subel.text = complet
    return None

def get_complet(cand):
    return get(cand, 'diagnostic/complet', '', 0)

def calcul_scoreb(cand):
    # Calcul du score brut
    # Récupération des coef
    if 'cpes' in get_clas_actu(cand).lower():
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
            note = get_note(cand, 'Première', mat, t)
            if note != '-':
                tot += vers_num(note)
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
                note = get_note(cand, 'Terminale', mat, t)
                if note != '-':
                    tot += vers_num(note)
                    nb += 1
        if nb > 0:
            moy_term = tot/nb
        else:
            moy_term = 0
    else: # candidat en terminale : 45% 1er trimestre ; 55% 2e trimestre
        if get_sem_term(cand) == 'on':
            for mat in matiere:
                note = get_note(cand, 'Terminale', mat, 'trimestre 1')
                if note != '-':
                    tot += vers_num(note)
                    nb += 1
        else:
            trim = ['trimestre 1','trimestre 2']
            for t in trim:
                for mat in matiere:
                    note = get_note(cand, 'Terminale', mat, t)
                    if note != '-':
                        if '1' in t:
                            tot += vers_num(note)*prop_prem_trim
                            nb += prop_prem_trim 
                        else:
                            tot+= vers_num(note)*(1-prop_prem_trim)
                            nb += 1-prop_prem_trim
        if nb > 0:
            moy_term = tot/nb
        else:
            moy_term = 0
    # moyenne EAF : 2/3 pour l'écrit et 1/3 pour l'oral
    tot = 0
    nb = 0
    note = get_ecrit_EAF(cand)
    if note != '-':
        tot += vers_num(note)*prop_ecrit_EAF
        nb += prop_ecrit_EAF
    note = get_oral_EAF(cand)
    if note != '-':
        tot += vers_num(note)*(1-prop_ecrit_EAF)
        nb += 1-prop_ecrit_EAF
    if nb > 0:
        moy_EAF = tot/nb
    else:
        moy_EAF = 0
    # éventuellement moyenne de CPES
    if coef['cpes']: # candidat en cpes
        tot = 0
        nb = 0
        note = get_CM1(cand, True)
        if note != '-':
            tot += vers_num(note)
            nb += 1
        note = get_CP1(cand, True)
        if note != '-':
            tot += vers_num(note)
            nb += 1
        if nb > 0:
            moy_cpes = tot/nb
        else:
            moy_cpes = 0
    # score brut
    tot = moy_prem*coef['Première']+moy_term*coef['Terminale']+moy_EAF*coef['EAF']
    nb = coef['Première']+coef['Terminale']+coef['EAF']
    if coef['cpes']:
        tot += moy_cpes*coef['cpes']
        nb += coef['cpes']
    scoreb = vers_str(tot/nb)
    try:
        cand.xpath('diagnostic/score')[0].text = scoreb
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'score')
        subel.text = scoreb
        
def set_rang_final(cand,rg):
    # Stockage rang final
    try:
        cand.xpath('diagnostic/rangf')[0].text = rg
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'rangf')
        subel.text = rg

def get_rang_final(cand):
    return get(cand, 'diagnostic/rangf', '?', 0)

def set_rang_brut(cand,rg):
    # Stockage rang brut
    try:
        cand.xpath('diagnostic/rangb')[0].text = rg
    except:
        el = cand.xpath('diagnostic')[0]
        subel = etree.SubElement(el, 'rangb')
        subel.text = rg

def get_rang_brut(cand):
    return get(cand, 'diagnostic/rangb', '?', 0)
