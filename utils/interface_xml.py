#!/usr/bin/env python3
#-*- coding: utf-8 -*-

from lxml import etree
from parse import parse
from utils.parametres import filieres

###################################
# Accesseur et mutateur standardisés
# Tous fonctionnant selon le même modèle, c'est plus léger ainsi
###################################
def get(cand, attr):
    # lit le champ désigné par 'query' relatif au candidat 'cand'
    # num vaut 'True' si la valeur à retourner est numérique
    try:
        result = cand.xpath(acces[attr]['query'])[0].text
        if 'post' in acces[attr].keys():
            result = acces[attr]['post'](result)
        if not(result): result = acces[attr]['defaut'] # évite un retour None si le champ est <blabla/>
    except:
        result = acces[attr]['defaut']
    return result

def set(cand, attr, value):
    # écrit le champ désigné par 'query' relatif au candidat 'cand'
    # si besoin, appelle la fonction _accro_branche qui construit
    #l'arborescence manquante dans le fichier xml
    query = acces[attr]['query']
    if 'pre' in acces[attr].keys():
        value = acces[attr]['pre'](value)
    try:
        cand.xpath(query)[0].text = value
    except:
        node = query.split('/')[-1]
        fils = etree.Element(node)
        fils.text = value
        pere = parse('{}/' + node, query)[0]
        _accro_branche(cand, pere, fils)

def _accro_branche(cand, pere, fils):
    # Reconstruction d'une arborescence incomplète. On procède
    # de manière récursive en commençant par l'extrémité (les feuilles !)...
    # pere est un chemin (xpath) et fils un etree.Element
    # ATTENTION : il ne faut pas d'espaces superflues dans la chaine pere.
    if cand.xpath(pere) != []: # test si pere est une branche existante
        cand.xpath(pere)[0].append(fils) # si oui, on accroche le fils
    else: # sinon on créé le père et on va voir le grand-père
        node = pere.split('/')[-1] # récupération du dernier champ du chemin
        if 'Chimie' in node: node=pere.split('/')[-2]+'/'+node # un traitement
        # particulier du fait que le champ contient '/' (Physique/Chimie)
        grand_pere = parse('{}/' + node, pere)[0] # le reste du chemin est le grand-pere
        # analyse et création du père avec tous ses champs...
        noeuds = parse('{}[{}]', node)
        if noeuds is None:
            noeuds = [node]
        pere = etree.Element(noeuds[0])
        if noeuds != [node]: # le père a d'autres enfants
            list = noeuds[1].split('][')
            for li in list:
                dico = parse('{nom}="{val}"', li)
                el = etree.Element(dico['nom'])
                el.text = dico['val']
                pere.append(el)
        pere.append(fils)
        _accro_branche(cand, grand_pere, pere)

###################################
# Fonctions de pré ou post traitement
###################################
def not_note(note):
    if not isnote(note):
        note = '-'
    return note

def convert(str):
    # formate la chaine 'str' contenant un nombre.
    # Intérêt seulement esthétique dans la page web
    return vers_str(vers_num(str))

def formate_candid(cc):
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
    return '-'.join(fil.upper() for fil in filieres if cc[filieres.index(fil)]!='-')

def formate_jury(jury):
    return parse('Jury {}', jury)[0]

def num_score(sc):
    if sc == 'NC': sc= '0'
    return sc

###################################
# Quelques fonctions de conversion et test
###################################
def isnote(note):
    # Teste si 'note' est bien un réel compris entre 0 et 20
    bool = True
    try:
        vers_num(note)
    except:
        bool = False
    return bool and vers_num(note)>=0 and vers_num(note)<=20

def vers_num(str):
    return float(str.replace(',','.'))

def vers_str(num):
    # Convertit un nombre en une chaîne formatée à 2 décimales
    str = '{:5.2f}'.format(num)
    return str.replace('.',',')

##################################
# Dictionnaire contenant les clés d'accès aux informations candidat.
# L'argument est encore un dictionnaire :
# Celui-ci DOIT contenir :
#       une clé 'query' pointant sur le path xml,
#       une clé 'defaut' pointant sur la valeur a renvoyer par défaut.
# et il PEUT contenir :
#       une clé 'pre' pointant sur une fonction de pré-traitement (avant set),
#       une clé 'post' pointant sur une fonction de post-traitement (après get).
##################################
acces = {\
        'Nom'               : {'query' : 'nom', 'defaut' : '?'},
        'Prénom'            : {'query' : 'prénom', 'defaut' : '?'},
        'Sexe'              : {'query' : 'sexe', 'defaut' : '?'},
        'Date de naissance' : {'query' : 'naissance', 'defaut' : '?'},
        'Classe actuelle'   : {'query' : 'synoptique/classe', 'defaut' : '?'},
        'Num ParcoursSup'   : {'query' : 'id_apb', 'defaut' : '?'},
        'INE'               : {'query' : 'INE', 'defaut' : '?'},
        'Nationalité'       : {'query' : 'nationalité', 'defaut' : '?'},
        'Boursier'          : {'query' : 'boursier', 'defaut' : '?'},
        'Boursier certifié' : {'query' : 'boursier_certifie', 'defaut' :'?'},
        'Établissement'     : {'query' : 'synoptique/établissement/nom', 'defaut' : '?'},
        'Commune'           : {'query' : 'synoptique/établissement/ville', 'defaut' : '?'},
        'Département'       : {'query' : 'synoptique/établissement/département', 'defaut' : '?'},
        'Pays'              : {'query' : 'synoptique/établissement/pays', 'defaut' : '?'},
        'Écrit EAF'         : {'query' : 'synoptique/français.écrit', 'defaut' : '-', 'pre' : not_note, 'post' : convert},
        'Oral EAF'          : {'query' : 'synoptique/français.oral', 'defaut' : '-', 'pre' : not_note, 'post' : convert},
        'Candidatures'      : {'query' : 'diagnostic/candidatures', 'defaut' : '???', 'pre' : formate_candid},
        'Candidatures impr' : {'query' : 'diagnostic/candidatures', 'defaut' : '???', 'post' : formate_impr_candid},
        'sem_prem'          : {'query' : 'diagnostic/sem_prem', 'defaut' : 'off'},
        'sem_term'          : {'query' : 'diagnostic/sem_term', 'defaut' : 'off'},
        'traité'            : {'query' : 'diagnostic/traité', 'defaut' : False},
        'Jury'              : {'query' : 'diagnostic/jury', 'defaut' : 'Auto', 'pre' : formate_jury},
        'Motifs'            : {'query' : 'diagnostic/motifs', 'defaut' : ''},
        'Score brut'        : {'query' : 'diagnostic/score', 'defaut' : ''},
        'Correction'        : {'query' : 'diagnostic/correc', 'defaut' : '0'},
        'Score final'       : {'query' : 'diagnostic/scoref', 'defaut' : ''},
        'Score final num'   : {'query' : 'diagnostic/scoref', 'defaut' : '0', 'post' : num_score},
        'Rang brut'         : {'query' : 'diagnostic/rangb', 'defaut' : '?'},
        'Rang final'        : {'query' : 'diagnostic/rangf', 'defaut' : '?'}
        }

# Pour les notes du lycée :
matiere = ['Mathématiques', 'Physique/Chimie']
date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
classe = ['Première', 'Terminale']
for cl in classe:
    for mat in matiere:
        for da in date:
            key = '{} {} {}'.format(mat, cl, da)
            query = 'bulletins/bulletin[classe="{}"]/matières/matière[intitulé="{}"][date="{}"]/note'.format(\
                    cl, mat, da)
            acces[key] = {'query' : query, 'defaut' : '-', 'pre' : not_note, 'post' : convert}

# Pour les notes CPES :
matiere = ['Mathématiques', 'Physique/Chimie']
for mat in matiere:
    key = '{} CPES'.format(mat)
    query = 'synoptique/matières/matière[intitulé="{}"]/note'.format(mat)
    acces[key] = {'query' : query, 'defaut' : '-', 'pre' : not_note, 'post' : convert}
