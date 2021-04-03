# pylint: disable=I1101
# I1101 car c'est lxml qui le déclenche beaucoup

"""Ce module fournit des fonctions pour lire un fichier csv exporté
par ParcoursSup et reformater ses données au format XML, qu'il peut
alors sauver.

"""

# Pour lire le csv de parcourssup, il faut commencer par regarder la
# première ligne et identifier dans l'ordre les différents
# champs. L'ordre est important, car on retrouve les mêmes noms au fur
# et à mesure de la lecture (il y a des doublons : on ne peut pas
# considérer le tableau comme un dictionnaire!). C'est aussi à ce
# moment que l'on pourra détecter d'une année sur l'autre si quelque
# chose d'important a changé. Une fois cela fait, on peut se lancer
# dans la lecture des autres lignes pour obtenir une liste de
# candidats.

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

import sys

from parse import parse

from lxml import etree

from utils.toolbox import num_to_col

#
# DESCRIPTION DE L'ÉTAT
#

class Etape(Enum):
    """Cette classe fournit une énumération des grandes étapes pour
    l'automate à états de la lecture.

    """

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
    """"Ce lecteur sert à finaliser le candidat qui était en construction
    et à l'ajouter dans la liste des candidats connus.

    """

    if etat['test']:
        print('clore_candidat')
    etat = clore_bulletin(etat, ligne)
    etat['candidats'].append(etat['candidat'])
    etat['candidat'] = nouveau_candidat()
    return etat

def clore_bulletin(etat, ligne):
    """Ce lecteur sert à finaliser le bulletin qui était en construction
    et à l'ajouter à la liste.

    """

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

def clore_etablissement(etat, _ligne):
    """Ce lecteur sert à finaliser la description de l'établissement telle
    qu'on peut la trouver dans la fiche synoptique ou les bulletins.

    """

    if etat['test']:
        print('clore_etablissement')

    if list(etat['établissement']) == []:
        return etat

    if etat['étape'] == Etape.SYNOPTIQUE:
        synoptique = etat['candidat'].xpath('synoptique')[0]
        synoptique.append(etat['établissement'])
    else:
        # FIXME: en trouve-t-on encore dans les bulletins!?
        etat['bulletin'].append(etat['établissement'])
    etat['établissement'] = nouvel_etablissement()

    return etat

def clore_matiere(etat, _ligne):
    """Ce lecteur sert à finaliser la lecture des informations sur une
    matière dans la fiche synoptique ou dans un bulletin.

    """

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

def transition_etape(etat, _ligne, val):
    """Ce lecteur procède à un changement d'état de l'automate de lecture
    d'une ligne d'une grande étape à une autre. Il ne lit pas...

    """
    if etat['test']:
        print('transition_etape vers {0:s}'.format(val))
    etat['étape'] = val
    return etat

def lecteur_note(etat, ligne, colonne, intitule, nature, _valeur):
    """Ce lecteur récupère une valeur portée dans une colonne ; il sait à
    quelle matière elle correspond (intitule) ainsi que sa nature
    (cela peut être une moyenne 'candidat', 'classe', 'plus
    petite'... mais aussi 'rang' ou 'effectif', donc ce n'est pas
    forcément une note!).

    """

    if etat['test']:
        print('lecteur_note[{0:s}] ({1:s}, {2:s})'.format(num_to_col(colonne+1),
                                                          intitule, nature))

    intitules = etat['matière'].xpath('intitulé')
    if intitules == []:
        intitule = etree.SubElement(etat['matière'], 'intitulé')
        intitule.text = intitule

    if ligne[colonne] != '':
        fils = etree.SubElement(etat['matière'], nature)
        fils.text = ligne[colonne]

    return etat

def lecteur_direct(etat, ligne, colonne, nom, champ):
    """Ce lecteur récupère directement une information principale dans une
    colonne (pas une information secondaire qui va aller dans un
    sous-arbre).

    """
    if etat['test']:
        print('lecteur_direct[{0:s}] ({1:s}, {2:s})'.format(num_to_col(colonne+1),
                                                            nom, champ))
    # inutile de récupérer plusieurs fois la même information
    if etat[nom].xpath(champ) != []:
        return etat
    if ligne[colonne] != '':
        fils = etree.SubElement(etat[nom], champ)
        fils.text = ligne[colonne]
    return etat

def lecteur_fixe(etat, _ligne, nom, champ, valeur):
    """Ce lecteur écrit une information qui a été notée ; par exemple le
    nom d'une matière, qui n'apparaît que dans l'entête de la colonne
    et pas sur la ligne courante.

    """

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
    """Ce lecteur récupère une information générale dans le tableau qui a
    trait à la fiche synoptique.

    """

    if etat['test']:
        print('lecteur_synoptique[{0:s}] ({1:s})'.format(num_to_col(colonne+1),
                                                         champ))
    if ligne[colonne] != '':
        synoptique = etat['candidat'].xpath('synoptique')[0]
        fils = etree.SubElement(synoptique, champ)
        fils.text = ligne[colonne]
    return etat

def lecteur_type_scolarite(etat, ligne, colonne):
    """Ce lecteur détecte si la scolarité est trimestrielle ou
    semestrielle.

    """

    if etat['test']:
        print('lecteur_type_scolarite[{0:s}] ({1:s})'.format(num_to_col(colonne+1),
                                                             ligne[colonne]))

    sem = etat['bulletin'].xpath('semestriel')
    if sem == []:
        sem = etree.SubElement(etat['bulletin'], 'semestriel')
    else: # ne devrait pas arriver
        sem = sem[0]
    if ligne[colonne] == 'Trimestrielle':
        sem.text = '0'
    elif ligne[colonne] == 'Semestrielle':
        sem.text = '1'
    else:
        sem.text = '-1'
    return etat

#
# fonctions de création des objets
#

def nouveau_candidat():
    """Cette fonction crée un nouveau nœud XML pour décrire un candidat,
    avec des sous-arbres prêts à accueillir les données.

    """
    res = etree.Element('candidat')
    etree.SubElement(res, 'bulletins')
    fils = etree.SubElement(res, 'synoptique')
    etree.SubElement(fils, 'matières')
    fils = etree.SubElement(res, 'diagnostic')
    fils = etree.SubElement(fils, 'score')
    fils.text = 'NC'
    return res

def nouvel_etablissement():
    """Cette fonction crée un nouveau nœud XML pour décrire un établissement"""
    return etree.Element('établissement')

def nouveau_bulletin():
    """Cette fonction crée un nouveau nœud XML pour décrire un bulletin"""
    res = etree.Element('bulletin')
    etree.SubElement(res, 'matières')
    return res

def nouvelle_matiere():
    """Cette fonction crée un nouveau nœud XML pour décrire une matière"""
    return etree.Element('matière')

#
# IMPLÉMENTATION DE LA RECONNAISSANCE DES CHAMPS
#

def prepare_lecteurs_informations_generales(champs, lecteurs, colonne, test = False):
    """Cette fonction reconnaît le premier groupe de colonnes, qui
    contient les informations générales.

    """
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
                print('Colonne {0:s}: généralité ({1:s})'.format(num_to_col(colonne+1),
                                                                 champs[colonne]))
            lecteurs.append(lambda e,l, a=colonne, b=directs[champs[colonne]]:
                            lecteur_direct(e, l, a, 'candidat', b))
            colonne = colonne + 1
            continue

        # on reconnaît le début de la fiche synoptique : fin du traitement ici
        if champs[colonne].endswith('établissement'):
            break

        # si on arrive ici, c'est qu'on n'a pas reconnu la colonne
        # courante dans cette étape ni comme le début de l'étape
        # suivante: à ignorer!
        if test:
            print('Colonne {0:s}: à ignorer ({1:s})'.format(num_to_col(colonne+1),
                                                            champs[colonne]))
        # pas de lecteurs.append ici, logiquement!
        colonne = colonne + 1

    return colonne

def prepare_lecteurs_fiche_synoptique(champs, lecteurs, colonne, test = False):
    """Cette fonction reconnaît le second groupe de colonnes, qui contient
    les informations de la fiche synoptique

    """
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
        'Spécialité/Mention/Voie': 'spécialité', # FIXME: en général vide: laisser tomber?
        'Méthode de travail': 'methode_travail',
        'Autonomie': 'autonomie',
        'Engagement citoyen': 'engagement_citoyen',
        "Capacité à s'investir": 'capacite_investissement',
        "Autres éléments d'appréciation": 'appreciation_subsidiaire',
        'Niveau de la classe': 'niveau_classe',
        'Avis sur la capacité à réussir': 'capacite_reussite',
        'Candidature validée (O/N)': 'candidature_validée',
    }

    # même organisation que pour la fonction
    # prepare_lecteurs_informations_generales avec une boucle et un
    # drapeau pour les mêmes raisons, mais apparition de matiere, qui
    # sert à se souvenir à propos de quelle matière on a lu des
    # informations : comme cela, si on voit des choses sur une autre
    # matière, on sait qu'il faut d'abord clore!
    matiere = ''
    while colonne < len(champs):

        n_col = num_to_col(colonne+1)
        titre = champs[colonne]

        # Cas particulier : cette colonne est une généralité sur le
        # candidat, mais elle est dans la partie fiche synoptique
        if titre == 'Numéro INE':
            if test:
                print(f"Colonne {n_col}: INE")
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'candidat', 'INE'))
            colonne = colonne + 1
            continue

        if titre in directs:
            champ = directs[titre]
            if test:
                print(f"Colonne {n_col}: {champ} de l'établissement ({titre})")
            lecteurs.append(lambda e, l, a=colonne, b=champ:
                            lecteur_direct (e, l, a, 'établissement', b))
            matiere = ''
            colonne = colonne + 1
            continue

        if titre in synoptique:
            nom = synoptique[titre]
            if test:
                print(f'Colonne {n_col}: {nom} (synoptique) ({titre})')
            lecteurs.append(lambda e, l, a=colonne, b=nom:
                            lecteur_synoptique(e, l, a, b))
            matiere = ''
            colonne = colonne + 1
            continue

        # reconnaissance d'un motif...
        res = parse('{} (note)', titre)
        if res:
            if res[0] != matiere:
                if test:
                    print(f'Colonne {n_col}: nouvelle matière')
                lecteurs.append(clore_matiere)
                matiere = res[0]
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe (e, l, 'matière', 'intitulé', a))
            if test:
                print(f"Colonne {n_col}: note en {matiere}")
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'matière', 'note'))
            colonne = colonne + 1
            continue

        res = parse('Classement ({})', titre)
        if res:
            if res[0] != matiere:
                if test:
                    print(f'Colonne {n_col}: nouvelle matière')
                lecteurs.append(clore_matiere)
                matiere = res[0]
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe(e, l, 'matière', 'intitulé', a))
            if test:
                print(f"Colonne {n_col}: rang en {matiere}")
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'matière', 'rang'))
            colonne = colonne + 1
            continue

        res = parse('Effectif ({})', titre)
        if res:
            if res[0] != matiere:
                if test:
                    print(f'Colonne {n_col}: nouvelle matière')
                lecteurs.append(clore_matiere)
                matiere = res[0]
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe(e, l, 'matière', 'intitulé', a))
            if test:
                print(f"Colonne {n_col}: effectif en {matiere}")
            lecteurs.append(lambda e, l, a=colonne:
                            lecteur_direct(e, l, a, 'matière', 'effectif'))
            colonne = colonne + 1
            continue

        # on reconnaît le début d'un bulletin: fin du traitement ici
        if titre in ['Année', 'Année scolaire']:
            break

        if test:
            print(f'Colonne {n_col}: à ignorer ({titre})')
        matiere = ''
        colonne = colonne + 1

    return colonne

def prepare_lecteurs_bulletins(champs, lecteurs, colonne, test = False):
    """Cette fonction reconnaît les derniers groupes de colonnes, qui sont
    successivement les différents bulletins.

    """
    if test:
        print('Début de la lecture des bulletins')
    lecteurs.append(lambda e, l: transition_etape(e, l, Etape.BULLETINS))

    directs_bulletin = {
        "Niveau d'étude": 'classe', # 'Seconde', 'Terminale', 'Non
                                    # scolarisé'

        # suivant les bulletins on trouve 'Classe' ou 'Série', avec le
        # même genre de données!
        'Classe': 'série', # 'Série Générale', 'Scientifique' (vieux),
                           # '' (non scolarisé)
        'Série': 'série', # 'Série Générale', 'Scientifique' (vieux),
                          # '' (non scolarisé)
    }

    matiere = ''
    while colonne < len(champs):

        titre = champs[colonne]
        n_col = num_to_col(colonne+1)

        # on reconnaît le début d'un bulletin à son année
        if titre.startswith('Année'):
            if test:
                print(f"Début d'un bulletin via sa date en colonne {n_col}")
            lecteurs.append(clore_bulletin)
            lecteurs.append(lambda e,l, a=colonne:
                            lecteur_direct (e, l, a, 'bulletin', 'année'))
            colonne = colonne + 1
            matiere = ''
            continue

        if titre in directs_bulletin:
            champ = directs_bulletin[titre]
            if test:
                print(f'La colonne {n_col} est une information de bulletin: {champ} ({titre})')
            lecteurs.append(lambda e,l, a=colonne, b=champ:
                            lecteur_direct(e, l, a, 'bulletin', b))
            colonne = colonne + 1
            matiere = ''
            continue

        if titre == 'Type de scolarité':
            if test:
                print(f'La colonne {n_col} est une information de bulletin: {titre}')
            lecteurs.append(lambda e,l, a=colonne:
                            lecteur_type_scolarite(e, l, a))
            colonne = colonne + 1
            continue

        res = parse('Moyenne {} en {} Trimestre {}', titre)
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
                    print(f'Colonne {n_col}: nouvelle matière')
                lecteurs.append(clore_matiere)
                matiere = quoi
                lecteurs.append(lambda e, l, a=matiere:
                                lecteur_fixe(e, l, 'matière', 'intitulé', a))
            if test:
                print(f"Colonne {n_col}: {qui} en {matiere}")
            lecteurs.append(lambda e, l, a=f'trimestre {quand}':
                            lecteur_fixe(e, l, 'matière', 'date', a))
            lecteurs.append(lambda e, l, a=colonne, b=qui:
                            lecteur_direct(e, l, a, 'matière', b))
            colonne = colonne + 1
            continue

        # on ignore tout le reste
        if test:
            print(f'La colonne {n_col} est à ignorer ({titre})')
        matiere = ''
        colonne = colonne + 1

    return colonne

def prepare_lecteurs(champs, test = False):
    """Cette fonction reçoit la liste des chaînes de la première ligne et
    renvoie la liste des lecteurs qui seront capables d'interpréter
    les autres lignes ; elle appelle donc successivement les
    différentes autres fonction prepare_*.

    """

    lecteurs = []
    colonne = 0

    if test:
        print("Début de la reconnaissance des champs")

    colonne = prepare_lecteurs_informations_generales(champs, lecteurs, colonne, test)
    colonne = prepare_lecteurs_fiche_synoptique(champs, lecteurs, colonne, test)
    colonne = prepare_lecteurs_bulletins(champs, lecteurs, colonne, test)
    lecteurs.append(clore_candidat)

    # On est peut-être arrivé là en pensant qu'on avait fini toutes
    # les étapes successives alors qu'en fait, on est juste tombés sur
    # une colonne qu'on ne connaissait pas : on sort en vitesse, il va
    # falloir adapter le code!
    if colonne < len(champs) and test:
        print(f'Il reste des colonnes non traitées à partir de la {num_to_col(colonne+1)}!')
        sys.exit(-1)

    if test:
        print('Fin de la reconnaissance des champs')

    return lecteurs

def execute_lecteurs(lecteurs, lignes, test = False):
    """Cette fonction est responsable de la lecture de toutes les lignes
    après la première : elle fait simplement tourner l'automate décrit
    par la liste des lecteurs obtenue à l'étape de reconnaissance des
    colonnes, ce qui construit au fur et à mesure le document XML
    décrivant les candidats.

    """

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
    for ligne in lignes:
        for lecteur in lecteurs:
            etat = lecteur(etat, ligne)

    return etat['candidats']

def lire(nom, test = False):
    """Cette fonction lit un fichier CSV obtenu de ParcoursSup et renvoie
    un document XML contenant les mêmes données.

    """
    with open(nom, encoding='utf-8-sig') as fich:
        reader = csv.reader(fich, delimiter=';')
        lecteurs = prepare_lecteurs(next(reader), test)
        candidats = execute_lecteurs(lecteurs, reader, test)
        candidats.sort(key = lambda candidat: candidat.xpath('nom')[0].text)
        res = etree.Element('candidats')
        for candidat in candidats:
            res.append(candidat)
        return res

def ecrire(nom, xml):
    """Cette fonction écrit des données XML dans un fichier"""
    with open(nom, 'wb') as fich:
        fich.write(etree.tostring(xml, pretty_print=True, encoding='utf-8'))
