# Pour lire le csv d'APB, il faut commencer par regarder la première
# ligne et identifier dans l'ordre les différents champs. L'ordre est
# important, car on retrouve les mêmes noms au fur et à mesure de la
# lecture (il y a des doublons : on ne peut pas considérer le tableau
# comme un dictionnaire!). C'est aussi à ce moment que l'on pourra
# détecter d'une année sur l'autre si quelque chose d'important a
# changé. Une fois cela fait, on peut se lancer dans la lecture des
# autres lignes pour obtenir une liste de candidats.

# Les premiers groupes de colonnes donnent les généralités, puis on
# trouve la fiche synoptique, puis les bulletins, donc la
# reconnaissance des colonnes va suivre ces trois grandes étapes.

# Pour chaque colonne, on va noter ce que l'on a reconnu et stocker un
# "lecteur", c'est-à-dire une fonction qui ira lire la donnée dans la
# bonne colonne et la stockera. Le résultat de la reconnaissance sera
# donc une liste de lecteurs. Ensuite, la lecture des candidats
# consistera à appeler tous les lecteurs dans l'ordre sur chaque
# ligne.

# Qu'est-ce qu'un lecteur? Il faut qu'il dispose de la ligne sur
# laquelle il doit lire les données, mais aussi qu'il puisse les
# écrire quelque part, donc il lui faut deux arguments : il reçoit en
# conséquence un état et une ligne, et renvoie un état modifié par son
# action. Une fois que l'on aura fait passer tous les lecteurs sur
# toutes les lignes, en passant à chacun successivement l'état enrichi
# par ses prédécesseurs, il suffira de récupérer le morceau qui nous
# intéresse.

# Que peut-on trouver dans l'état? Aucune donnée ne s'offre à nous
# directement : la liste des candidats s'obtient par accrétion des
# candidats, chaque candidat par agrégation de données générales,
# d'une fiche synoptique et de bulletins, etc. On va donc devoir
# stocker des objets incomplets, dans lesquels les lecteurs vont
# ajouter des données, et régulièrement, déclarer qu'il est complet,
# le stocker dans son conteneur normal et repartir avec un nouvel
# objet vide : certains lecteurs ne vont donc rien lire sur la ligne,
# mais vont modifier l'état pour clore un objet (il faut que chacun de
# ceux-ci soient idempotents). Enfin, le changement d'étape se fait
# aussi avec un lecteur, qui ne lit rien, mais modifie l'état.

# Techniquement, qu'est-ce qu'un lecteur? Une fonction! On va donc
# stocker des fonctions. Cependant, c'est une fonction qui va devoir
# être partiellement évaluée, parce qu'elle voudra accepter l'état et
# la ligne, mais devra se souvenir de la colonne dans laquelle elle
# lit et comment elle doit modifier l'état. Les fonctions anonymes
# (lambda) tendent les bras pour remplir ce rôle, mais attention:
# elles ne capturent pas leurs données si on ne les y force pas, donc
# si on tente:
#
# colonne = 2
# f = lambda e, l: e['toto'] = l[colonne]
# colonne = 3
# f(e,l) # oups! colonne vaut 3!
#
# La solution est:
#
# colonne = 2
# f = lambda e, l, a=colonne: e['toto'] = l[a]
# colonne = 3
# f(e,l) # ok!

import csv
from enum import Enum

from parse import parse

from lxml import etree

from .parametres import annee_terminale

#
# DESCRIPTION DE L'ÉTAT
#

class Etape(Enum):
    GENERALITES = 1
    SYNOPTIQUE = 2
    BULLETINS = 3

# L'état de la lecture est un dictionnaire, avec pour clefs :
#
# 'étape': l'Etape(Enum) qui décrit où on en est
# 'matière': contient la matière en cours de lecture
# 'établissement': contient l'établissement en cours de lecture
# 'bulletin': le bulletin en cours de lecture
# 'candidat': le candidat en cours de lecture
# 'candidats': liste des candidats déjà complets
#
# 'test': booléen, vrai si on veut que les lecteurs racontent ce qu'ils font

#
# IMPLÉMENTATION DE DIVERS LECTEURS
#

def clore_candidat(etat, ligne):
    if etat['test']:
        print('clore_candidat')
    etat = clore_bulletin(etat, ligne)
    etat['candidats'].append(etat['candidat'])
    etat['candidat'] = nouveau_candidat()
    return etat

def clore_bulletin(etat, ligne):
    if etat['test']:
        print('clore_bulletin')
    etat = clore_matiere(etat, ligne)
    etat = clore_etablissement(etat, ligne)

    if (len(etat['bulletin']) <= 1
        and len(etat['bulletin'].xpath('matières')[0]) == 0):
        return etat

    if etat['étape'] == Etape.SYNOPTIQUE:
        return etat

    bulletins = etat['candidat'].xpath('bulletins')[0]
    bulletins.append(etat['bulletin'])
    etat['bulletin'] = nouveau_bulletin()

    return etat

def clore_etablissement(etat, ligne):
    if etat['test']:
        print('clore_etablissement')

    if list(etat['établissement']) == []:
        return etat

    if etat['étape'] == Etape.SYNOPTIQUE:
        synoptique = etat['candidat'].xpath('synoptique')[0]
        synoptique.append(etat['établissement'])
    else:
        etat['bulletin'].append(etat['établissement'])
    etat['établissement'] = nouvel_etablissement()

    return etat

def clore_matiere(etat, ligne):
    if list(etat['matière']) == []:
        if etat['test']:
            print('clore_matiere (triviale)')
        return etat

    if etat['test']:
        print('clore_matiere (non triviale)')
    if etat['étape'] == Etape.SYNOPTIQUE:
        matieres = etat['candidat'].xpath('synoptique/matières')[0]
        matieres.append(etat['matière'])
    else:
        matieres = etat['bulletin'].xpath('matières')[0]
        matieres.append(etat['matière'])
    etat['matière'] = nouvelle_matiere()

    return etat

def transition_etape(etat, ligne, val):
    if etat['test']:
        print('transition_etape vers {0:s}'.format(val))
    etat['étape'] = val
    return etat

def lecteur_note(etat, ligne, colonne, intitule, nature, valeur):
    # nature peut par exemple être une 'plus petite', 'plus grande',
    # mais aussi 'rang' ou 'effectif', par exemple
    if etat['test']:
        print('lecteur_note[{0:s}] ({1:s}, {2:s})'.format(n2c(colonne+1),
                                                          intitule, nature))

    intitules = etat['matière'].xpath('intitulé')
    if intitules == []:
        intitule = etree.SubElement(etat['matière'], 'intitulé')
        intitule.text = intitule

    if ligne[colonne] != '':
        fils = etree.SubElement(etat['matière'], nature)
        fils.text = ligne[colonne]

    return etat

# ce lecteur lit directement dans une colonne une des informations principales
def lecteur_direct(etat, ligne, colonne, nom, champ):
    if etat['test']:
        print('lecteur_direct[{0:s}] ({1:s}, {2:s})'.format(n2c(colonne+1),
                                                            nom, champ))
    # inutile de récupérer plusieurs fois la même information
    if etat[nom].xpath(champ) != []:
        return etat
    if ligne[colonne] != '':
        fils = etree.SubElement(etat[nom], champ)
        fils.text = ligne[colonne]
    return etat

# ce lecteur écrit une constante à un endroit donné (le nom de la
# matière est dans l'entête de la colonne, pas sur la ligne, par exemple)
def lecteur_fixe(etat, ligne, nom, champ, valeur):
    if etat['test']:
        print('lecteur_fixe ({0:s}, {1:s}) = {2:s}'.format(nom, champ, valeur))
    # si on a déjà l'info, inutile de la remettre
    if etat[nom].xpath(champ) != []:
        return etat
    if valeur != '': # ne devrait pas arriver, mais c'est plus sûr
        fils = etree.SubElement(etat[nom], champ)
        fils.text = valeur
    return etat

def lecteur_synoptique(etat, ligne, colonne, champ):
    if etat['test']:
        print('lecteur_synoptique[{0:s}] ({1:s})'.format(n2c(colonne+1),
                                                         champ))
    if ligne[colonne] != '':
        synoptique = etat['candidat'].xpath('synoptique')[0]
        fils = etree.SubElement(synoptique, champ)
        fils.text = ligne[colonne]
    return etat

#
# fonctions de création des objets
#

def nouveau_candidat():
    res = etree.Element('candidat')
    etree.SubElement(res, 'bulletins')
    fils = etree.SubElement(res, 'synoptique')
    etree.SubElement(fils, 'matières')
    fils = etree.SubElement(res, 'diagnostic')
    fils = etree.SubElement(fils, 'score')
    fils.text = 'NC'
    return res

def nouvel_etablissement():
    return etree.Element('établissement')

def nouveau_bulletin():
    res = etree.Element('bulletin')
    etree.SubElement(res, 'matières')
    return res

def nouvelle_matiere():
    return etree.Element('matière')


#
# FONCTIONS DE POST-TRAITEMENT
#

# certains bulletins contiennent toutes les notes et l'année, la
# plupart tout le bulletin sauf les notes ; il faut donc trouver les
# notes et les déplacer où on veut.

def fusionne_bulletins(candidat, test = False):

    # on trouve la liste des bulletins sans note:
    probs = candidat.xpath('bulletins/bulletin[matières[not(matière)]]')
    for prob in probs:
        # là, normalement, c'est une fausse boucle : on ne devrait avoir
        # qu'une année!
        for node in prob.xpath('année'):
            annee = node.text
            autres = candidat.xpath('bulletins/bulletin[année = "{0:s}"]'.format(annee))
            autres.remove(prob)
            # ok, on a tous les doublons maintenant (normalement: 0 ou 1)
            for doublon in autres:
                prob.xpath('matières')[0].extend(doublon.xpath('matières/matière'))
                candidat.xpath('bulletins')[0].remove(doublon)

    return candidat

# Si le candidat est en terminale, sa classe sera dans la fiche
# synoptique et pas dans le bulletin de terminale, donc il faut qu'on
# recopie cette information.

def trouve_terminale(candidat, test = False):
    bulletins_courant = candidat.xpath('bulletins/bulletin[année = "{0:s}"]'.format(annee_terminale))
    if bulletins_courant != []:
        bulletin_courant = bulletins_courant[0]
        if bulletin_courant.xpath('classe') == []:
            classes = candidat.xpath('synoptique/classe')
            if classes != []:
                fils = etree.SubElement(bulletin_courant, 'classe')
                fils.text = classes[0].text
    return candidat

#
# IMPLÉMENTATION DE LA RECONNAISSANCE DES CHAMPS
#

def prepare_lecteurs(champs, test = False):
    "Reçoit la liste des chaînes de la première ligne et renvoie la liste"
    "des lecteurs qui seront capables d'interpréter les autres lignes"

    lecteurs = []
    colonne = 0

    if test:
        print("Début de la reconnaissance des champs")

    # lecture des informations générales

    lecteurs.append(lambda e, l: transition_etape(e, l, Etape.GENERALITES))
    if test:
        print('Début de la lecture des informations générales')

    directs = {
        'Numéro': 'id_apb',
        'Nom': 'nom',
        'Prénom': 'prénom',
        'Sexe': 'sexe',
        'Date de naissance': 'naissance',
        'Nationalité': 'nationalité',
        'Boursier': 'boursier',
        'Boursier certifié': 'boursier_certifie'
    }

    # cette organisation avec une boucle permet de résister à un
    # changement de l'ordre des colonnes dans une même étape
    while colonne < len(champs):

        if champs[colonne] in directs:
            if test:
                print('Colonne {0:s}: généralité ({1:s})'.format(n2c(colonne+1),
                                                                 champs[colonne]))
            lecteurs.append(lambda e,l, a=colonne, b=directs[champs[colonne]]:
                            lecteur_direct(e, l, a, 'candidat', b))
            colonne = colonne + 1
            continue

        # on reconnaît le début de la fiche synoptique
        if champs[colonne].endswith('établissement'):
            break

        # si on arrive ici, c'est qu'on n'a pas reconnu la colonne
        # courante dans cette étape ni comme le début de l'étape
        # suivante: à ignorer!
        if test:
            print('Colonne {0:s}: à ignorer ({1:s})'.format(n2c(colonne+1),
                                                            champs[colonne]))
        # pas de lecteurs.append ici, logiquement!
        colonne = colonne + 1
        continue # pas nécessaire mais plus propre et évite les ennuis à terme

    # lecture de la fiche synoptique

    lecteurs.append(lambda e, l: transition_etape(e, l, Etape.SYNOPTIQUE))
    if test:
        print('Début de la lecture de la fiche synoptique')

    directs = {
        'Libellé établissement': 'nom',
        'Commune établissement': 'ville',
        'Département établissement': 'département',
        'Pays établissement': 'pays',
        'Téléphone établissement': 'téléphone', # pour J!
    }
    synoptique = {
        "Type de formation": 'classe',
        'Série/Domaine/Filière': 'filière',
        'Spécialité/Mention/Voie': 'spécialité',
        'Niveau de la classe': 'niveau_classe',
        'Avis du CE': 'avis',
    }

    # même organisation avec une boucle et un drapeau encore, pour les
    # mêmes raisons, mais apparition de matiere, qui sert à se
    # souvenir à propos de quelle matière on a lu des informations :
    # comme cela, si on voit des choses sur une autre matière, on sait
    # qu'il faut d'abord clore!
    matiere = ''
    while colonne < len(champs):

        # Cas particulier : cette colonne est une généralité sur le
        # candidat, mais elle est dans la partie fiche synoptique
        if champs[colonne] == 'Numéro INE':
            if test:
                print("Colonne {0:s}: INE".format(n2c(colonne+1)))
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'candidat', 'INE'))
            colonne = colonne + 1
            continue

        if champs[colonne] in directs:
            champ = directs[champs[colonne]]
            if test:
                print("Colonne {0:s}: {1:s} de l'établissement ({2:s})".format(n2c(colonne+1), champ, champs[colonne]))
            lecteurs.append(lambda e, l, a=colonne, b=champ:
                            lecteur_direct (e, l, a, 'établissement', b))
            matiere = ''
            colonne = colonne + 1
            continue

        if champs[colonne] in synoptique:
            nom = synoptique[champs[colonne]]
            if test:
                print('Colonne {0:s}: {1:s} (synoptique) ({2:s})'.format(n2c(colonne+1), nom, champs[colonne]))
            lecteurs.append(lambda e, l, a=colonne, b=nom:
                            lecteur_synoptique(e, l, a, b))
            matiere = ''
            colonne = colonne + 1
            continue

        # reconnaissance d'un motif...
        res = parse('{} (note)', champs[colonne])
        if res:
            if res[0] != matiere:
                if test:
                    print('Colonne {0:s}: nouvelle matière'.format(n2c(colonne+1)))
                lecteurs.append(clore_matiere)
                matiere = res[0]
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe (e, l, 'matière', 'intitulé', a))
            if test:
                print("Colonne {0:s}: note en {1:s}".format(n2c(colonne+1),
                                                            matiere))
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'matière', 'note'))
            colonne = colonne + 1
            continue

        res = parse('Classement ({})', champs[colonne])
        if res:
            if res[0] != matiere:
                if test:
                    print('Colonne {0:s}: nouvelle matière'.format(n2c(colonne+1)))
                lecteurs.append(clore_matiere)
                matiere = res[0]
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe(e, l, 'matière', 'intitulé', a))
            if test:
                print("Colonne {0:s}: rang en {1:s}".format(n2c(colonne+1),
                                                            matiere))
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'matière', 'rang'))
            colonne = colonne + 1
            continue

        res = parse('Effectif ({})', champs[colonne])
        if res:
            if res[0] != matiere:
                if test:
                    print('Colonne {0:s}: nouvelle matière'.format(n2c(colonne+1)))
                lecteurs.append(clore_matiere)
                matiere = res[0]
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe(e, l, 'matière', 'intitulé', a))
            if test:
                print("Colonne {0:s}: effectif en {1:s}".format(n2c(colonne+1),
                                                                matiere))
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'matière', 'effectif'))
            colonne = colonne + 1
            continue

        if champs[colonne] == "Note à l'épreuve de Ecrit de Français (épreuve anticipée)":
            if test:
                print("Colonne {0:s}: note d'écrit de français".format(n2c(colonne+1)))
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_synoptique(e, l, a, 'français.écrit'))
            colonne = colonne + 1
            continue

        if champs[colonne] == "Note à l'épreuve de Oral de Français (épreuve anticipée)":
            if test:
                print("Colonne {0:s}: note d'oral de français".format(n2c(colonne+1)))
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_synoptique(e, l, a, 'français.oral'))
            colonne = colonne + 1
            continue

        # début d'un bulletin
        if champs[colonne] in ['Année', 'Année scolaire']:
            break

        if test:
            print('Colonne {0:s}: à ignorer ({1:s})'.format(n2c(colonne+1),
                                                            champs[colonne]))
        matiere = ''
        colonne = colonne + 1
        continue

    lecteurs.append(clore_bulletin)

    # lecture des bulletins

    if test:
        print('Début de la lecture des bulletins')
    lecteurs.append(lambda e, l: transition_etape(e, l, Etape.BULLETINS))

    directs_etablissement = {
        'Code établissement': 'code',
        'Libelle établissement': 'nom',
        'Ville établissement': 'ville',
        'Département établissement': 'département',
        'Pays établissement': 'pays',
    }
    directs_bulletin = {
        "Niveau d'étude": 'classe', # plutôt que "Type de formation"
                                    # qui est vide pour ceux qui ne
                                    # sont pas scolarisés!
        'Classe': 'série', # L, S, ES?
        'Série': 'série', # hmmm... douteux : FIXME?
        'LV1': 'LV1',
        'LV2': 'LV2',
    }

    matiere = ''
    while colonne < len(champs):

        # on reconnaît le début d'un bulletin à son année
        if champs[colonne] in ['Année', 'Année scolaire']:
            if test:
                print("Début d'un bulletin via sa date en colonne {0:s}".format(n2c(colonne+1)))
            lecteurs.append(clore_bulletin)
            lecteurs.append(lambda e,l, a=colonne:
                            lecteur_direct (e, l, a, 'bulletin', 'année'))
            colonne = colonne + 1
            matiere = ''
            continue

        if champs[colonne] in directs_etablissement:
            champ = directs_etablissement[champs[colonne]]
            if test:
                print("La colonne {0:s} est une information d'établissement: {1:s} ({2:s})".format(n2c(colonne+1), champ, champs[colonne]))
            lecteurs.append(lambda e,l, a=colonne, b=champ:
                            lecteur_direct(e, l, a, 'établissement', b))
            colonne = colonne + 1
            matiere = ''
            continue

        if champs[colonne] in directs_bulletin:
            champ = directs_bulletin[champs[colonne]]
            if test:
                print('La colonne {0:s} est une information de bulletin: {1:s} ({2:s})'.format(n2c(colonne+1), champ, champs[colonne]))
            lecteurs.append(lambda e,l, a=colonne, b=champ:
                            lecteur_direct(e, l, a, 'bulletin', b))
            colonne = colonne + 1
            matiere = ''
            continue

        res = parse('Moyenne {} en {} Trimestre {}', champs[colonne])
        if res:
            qui, quoi, quand = res
            # avec ça, on est sûr de casser en cas de changement
            correspondances = {
                'candidat': 'note',
                'classe': 'classe',
                'plus basse': 'mini',
                'plus haute': 'maxi'
            }
            qui = correspondances[qui]
            if quoi != matiere:
                if test:
                    print('Colonne {0:s}: nouvelle matière'.format(n2c(colonne+1)))
                lecteurs.append(clore_matiere)
                matiere = quoi
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe(e, l, 'matière', 'intitulé', a))
            if test:
                print("Colonne {0:s}: {1:s} en {2:s}".format(n2c(colonne+1),
                                                             qui, matiere))
            lecteurs.append(lambda e, l, a='trimestre {0:s}'.format(quand):
                            lecteur_fixe(e, l, 'matière', 'date', a))
            lecteurs.append(lambda e, l, a=colonne, b=qui:
                            lecteur_direct(e, l, a, 'matière', b))
            colonne = colonne + 1
            continue


        # on ignore tout le reste
        if test:
            print('La colonne {0:s} est à ignorer ({1:s})'.format(n2c(colonne+1), champs[colonne]))
        matiere = ''
        colonne = colonne + 1
        continue

    lecteurs.append(clore_candidat)

    # On est peut-être arrivé là en pensant qu'on avait fini toutes
    # les étapes successives alors qu'en fait, on est juste tombés sur
    # une colonne qu'on ne connaissait pas: on sort en vitesse, il va
    # falloir adapter le code!
    if colonne < len(champs) and test:
        print('Il reste des colonnes non traitées à partir de la {0:s}!'.format(n2c(colonne+1)))
        exit(-1)

    if test:
        print('Fin de la reconnaissance des champs')

    return lecteurs

# cette fonction a le beau rôle : elle n'a presque plus rien à faire!
def execute_lecteurs(lecteurs, csv, test = False):

    # définition de l'état initial
    etat = dict()
    etat['test'] = test
    etat['candidats'] = []
    etat['étape'] = Etape.GENERALITES
    etat['candidat'] = nouveau_candidat()
    etat['établissement'] = nouvel_etablissement()
    etat['bulletin'] = nouveau_bulletin()
    etat['matière'] = nouvelle_matiere()

    # on chaîne les lignes et les lecteurs
    for ligne in csv:
        for lecteur in lecteurs:
            etat = lecteur(etat, ligne)

    # on procède à l'assainissement de ce qui est encore un peu brut,
    # par étapes successives
    res = [fusionne_bulletins(candidat, test)
           for candidat in etat['candidats']]
    res = [trouve_terminale(candidat, test)
           for candidat in res]

    return res

def lire(nom, test = False):
    with open(nom, encoding='utf-8-sig') as fich:
        reader = csv.reader(fich, delimiter=';')
        lecteurs = prepare_lecteurs(next(reader), test)
        candidats = execute_lecteurs(lecteurs, reader, test)
        candidats.sort(key = lambda candidat: candidat.xpath('nom')[0].text)
        res = etree.Element('candidats')
        [res.append(candidat) for candidat in candidats]
        return res

#
# FONCTIONS DIVERSES
#

def n2c(num):
    'Convertit un numéro de colonne vers son nom dans un tableur'
    n = num
    res = ''
    tmp = 0
    while n > 0:
        mod = (n-1) % 26
        res = chr(65+mod) + res
        n = (n-mod) // 26
    return res
