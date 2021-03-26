#!/usr/bin/env python3
#-*- coding: utf-8 -*-
# pylint: disable=I1101
# I1101 car lxml le déclenche beaucoup

# Ce fichier contient la classe Fichier.

# Cette classe dispose d'un attribut important, le dictionnaire
# 'acces'. Il est ce qui traduit les requêtes extérieures (venant des
# clients) en requêtes xpath désignant le chemin dans le fichier xml.
# Les méthodes de classe 'set' et 'get' se chargent d'écrire et de
# lire les infos au bon endroit.

# Ce qui prévaut dans ce choix de structure : l'encapsulation. Les
# clients n'ont pas besoin de savoir quel type de fichier contient
# l'information qu'ils désirent. C'est le travail de la classe
# 'Fichier'. Il sera alors aisé (si le besoin s'en fait sentir) de
# changer de format de données..

###
#   Chaque instance Fichier est construite à partir d'un nom de fichier xml.
#   Son attribut principal est 'dossiers' : liste de noeuds candidat.
#   Cet objet réunit toutes les méthodes agissant sur ces dossiers et celles
#   qui agissent sur le contenu des dossiers : les candidatures.
###

from parse import parse
from lxml import etree

from config import filieres
from utils.parametres import coef_cpes
from utils.parametres import coef_term
from utils.toolbox import *

#################################################################################
#                               Fichier                                         #
#################################################################################
class Fichier:
    """objet fichier : son but est de contenir toutes les méthodes qui
    agissent sur le contenu des fichiers, i.e. les dossiers de
    candidatures. Ces fichiers sont des attributs des objets 'Client'
    que gère l'objet 'Serveur'.

    """

    ############# Méthodes de classe ##############

    @classmethod
    def get(cls, cand, attr):
        """accesseur : récupère le contenu d'un noeud xml cand est un
        etree.Element pointant un candidat attr est une clé du
        dictionnaire 'acces' défini ci-dessous

        """

        # Le dictionnaire 'acces' contient le chemin xpath relatif à
        # l'attribut attr et éventuellement le nom d'une fonction de
        # post-traitement. Celle-ci sert à mettre en 'forme' la valeur
        # lue (nécessairement de type string) pour l'usage auquel elle
        # est destinée. 'acces' contient également la valeur à
        # renvoyer dans le cas où le noeud n'existe pas (valeur par
        # défaut).
        cls_attr = cls.acces[attr]
        try:
            result = cand.xpath(cls_attr['query'])[0].text
            if 'post' in cls_attr:
                result = cls_attr['post'](result)
        except:
            result = None
        if not result:
            result = cls_attr['default'] # init_acces garantit que ça marche
        return result

    @classmethod
    def set(cls, cand, attr, value):
        """mutateur : écrit le contenu d'un noeud xml cand est un
         etree.Element pointant un candidat attr est une clé du
         dictionnaire 'acces' défini ci-dessus value est la valeur à
         écrire dans le noeud choisi.  Si le noeud n'existe pas, la
         fonction accro_branch (ci-après) reconstituera l'arborescence
         manquante.
        """

         # 'acces' contient éventuellement une le nom d'une fonction
         # de pré-traitement. Celle-ci sert à préparer la valeur à
         # être stockée dans le fichier xml.
        query = cls.acces[attr]['query']
        if 'pre' in cls.acces[attr]:
            value = cls.acces[attr]['pre'](value)
        try:
            cand.xpath(query)[0].text = value
        except:
            node = query.split('/')[-1]
            fils = etree.Element(node)
            fils.text = value
            pere = parse('{}/' + node, query)[0]
            cls._accro_branche(cand, pere, fils)

    @classmethod
    def _accro_branche(cls, cand, pere, fils):
        """Reconstruction d'une arborescence incomplète. On procède de manière
        récursive en commençant par l'extrémité (les feuilles !)...
        pere est un chemin (xpath) et fils un etree.Element

        ATTENTION : il ne faut pas d'espaces superflues dans la chaine
        pere.

        """

        if cand.xpath(pere) != []: # test si pere est une branche existante
            cand.xpath(pere)[0].append(fils) # si oui, on accroche le fils
        else: # sinon on créé le père et on va voir le grand-père

            # récupération du dernier champ du chemin
            node = pere.split('/')[-1]

             # un traitement particulier quand le champ contient (Physique/Chimie)
            if node.startswith('Chimie'):
                node=pere.split('/')[-2]+'/'+node
            grand_pere = parse('{}/' + node, pere)[0] # le reste du chemin est le grand-pere
            # analyse et création du père avec tous ses champs...
            noeuds = parse('{}[{}]', node)
            if noeuds is None:
                noeuds = [node]
            pere = etree.Element(noeuds[0])
            if noeuds != [node]: # le père a d'autres enfants
                for li in noeuds[1].split(']['):
                    dico = parse('{nom}="{val}"', li)
                    el = etree.Element(dico['nom'])
                    el.text = dico['val']
                    pere.append(el)
            pere.append(fils)
            cls._accro_branche(cand, grand_pere, pere)

    @classmethod
    def is_cpes(cls, cand):
        """ Renvoie True si le candidat est en CPES """
        return 'cpes' in cls.get(cand, 'Classe actuelle').lower()

    @classmethod
    def is_math_expertes(cls, cand):
        """Renvoie True si le candidat a au moins une note d'option math
        expertes
        """

        expert = False # initialisation
        # Construction de l'ensemble des champs à vérifier
        champs = {'Mathématiques Expertes Terminale trimestre {}'.format(j) for j in range(1,4)}

        # Dès qu'un champ est renseigné on arrête et renvoie True
        while len(champs) > 0:
            ch = champs.pop()
            if cls.get(cand, ch) != cls.acces[ch]['default']: # champ renseigné ?
                expert = True
                break
        return expert

    @classmethod
    def is_premiere_semestrielle(cls, cand):
        """Renvoie True si le candidat est noté en semestres en première

        """
        return cls.get(cand, 'Première semestrielle') == '1'

    @classmethod
    def is_terminale_semestrielle(cls, cand):
        """Renvoie True si le candidat est noté en semestres en terminale

        """
        return cls.get(cand, 'Terminale semestrielle') == '1'

    @classmethod
    def is_complet(cls, cand):
        """Renvoie True si tous les éléments nécessaires à un calcul correct
        du score brut sont présents"""

        # Cette fonction est appelée dans nettoie.py. Si elle renvoie
        # False, une alerte est mise en place et l'admin doit faire
        # tout ce qu'il peut pour la lever..  Les éléments à vérifier
        # sont lus dans parametres.py (coef...)  Construction de
        # l'ensemble des champs à vérifier
        champs = set()
        if cls.is_cpes(cand):
            coefs = coef_cpes
            en_term = False
        else:
            coefs = coef_term
            en_term = True

        for key, coef in coefs.items():

            # on ajoute à champ si coef non nul, si
            # math_expertes et option du candidat et si
            # les trimestres 'ne sont pas' des semestres

            ajout = not coef == 0
            ajout = ajout \
                and not ('expertes' in key.lower() \
                         and not cls.is_math_expertes(cand))
            ajout = ajout \
                and not ('première trimestre 3' in key.lower() \
                         and cls.is_premiere_semestrielle(cand))
            ajout = ajout \
                and not ('terminale trimestre 3' in key.lower() \
                         and cls.is_terminale_semestrielle(cand))
            ajout = ajout \
                and not (en_term and cls.is_terminale_semestrielle(cand) \
                         and 'terminale trimestre 2' in key.lower())

            if ajout:
                champs.add(key)

        # Tests :
        complet = not cls.get(cand, 'Classe actuelle') == cls.acces['Classe actuelle']['default']

        # Dès qu'un champ manque à l'appel on arrête et renvoie False
        while complet and len(champs) > 0:
            ch = champs.pop()
            if cls.get(cand, ch) == cls.acces[ch]['default']: # note non renseignée ?
                complet = False
        return complet

    @classmethod
    def calcul_scoreb(cls, cand):
        """ Calcul du score brut et renseignement du noeud xml """

        # Si correction = 'NC', cela signifie que l'admin rejette le
        # dossier ; score nul d'office!
        if cls.get(cand, 'Correction') == 'NC': # candidat rejeté
            cls.set(cand, 'Score brut', num_to_str(0))
            return

        # Récupération des coefficients, en les copiant car si
        # l'organisation est semestrielle, on va vouloir faire des
        # reports pour maintenir les poids relatifs
        if cls.is_cpes(cand):
            coef = dict(coef_cpes)
            # report coef de terminale si notation semestrielle
            if cls.is_terminale_semestrielle(cand):
                for key, val in coef.items():
                    if 'Terminale trimestre 3' in key:
                        coef[key.replace('trimestre 3', 'trimestre 1')] += val/2
                        coef[key.replace('trimestre 3', 'trimestre 2')] += val/2
        else:
            coef = dict(coef_term)
            # report coef de terminale si notation semestrielle
            if cls.is_terminale_semestrielle(cand):
                for key, val in coef.items():
                    if 'Terminale trimestre 2' in key:
                        coef[key.replace('trimestre 2', 'trimestre 1')] += val

        # Report des coef de première si notation semestrielle
        if cls.is_premiere_semestrielle(cand) == '1':
            for key, val in coef.items():
                if 'Première trimestre 3' in key:
                    coef[key.replace('trimestre 3', 'trimestre 1')] += val/2
                    coef[key.replace('trimestre 3', 'trimestre 2')] += val/2

        # Il y a aussi des reports si le candidat ne suit pas l'option math expertes
        if not cls.is_math_expertes(cand):
            for key,val in coef.items():
                if 'Expertes' in key:
                    coef[key.replace('Expertes', 'Spécialité')] += val

        # On a maintenant tout ce qu'il faut pour lancer le calcul
        somme, poids = 0, 0
        for key, val in coef.items():
            note = cls.get(cand, key)
            if note != cls.acces[key]['default']:
                somme += str_to_num(note)*val
                poids += val
        if poids != 0:
            scoreb = somme/poids
        else: # ne devrait pas arriver
            scoreb = 0
        # Bonus pour les cpes ou les math expertes...
        if (cls.is_cpes(cand) or cls.is_math_expertes(cand)):
            scoreb += 5
        cls.set(cand, 'Score brut', num_to_str(scoreb))

    @classmethod
    def rang(cls, cand, dossiers, critere):
        """ Trouver le rang d'un candidat dans une liste de dossiers, selon un critère donné """
        rg = 1
        score = lambda ca: float(cls.get(ca, critere).replace(',','.'))
        # On traite le cas d'un candidat non encore traité : son score est une chaîne vide !
        score_cand = 0
        if cls.get(cand, critere) != '':
            score_cand = score(cand)
        if dossiers:
            while (rg <= len(dossiers) and score(dossiers[rg-1]) > score_cand):
                rg+= 1
        return rg
    #                                             #
    ############ Fin méthodes de classe ###########

    ############## Attributs de classe #############
    ## _criteres_tri : contient les fonctions qui sont les clés de tri de la méthode
    # 'ordonne' définie plus bas..
    _criteres_tri = {
            'score_b' : lambda cand: -float(Fichier.get(cand, 'Score brut').replace(',','.')),
            'score_f' : lambda cand: -float(Fichier.get(cand, 'Score final').replace(',','.')),
            'alpha' : lambda cand: Fichier.get(cand, 'Nom')
            }

    ## acces : dictionnaire contenant les clés d'accès aux informations candidat
    # L'argument est encore un dictionnaire :
    # Celui-ci DOIT contenir :
    #       une clé 'query' donnant le path xml,
    #       une clé 'default' donnant la valeur à renvoyer par défaut.
    # et il PEUT contenir :
    #       une clé 'pre' donnant une fonction de pré-traitement (avant set),
    #       une clé 'post' donnant une fonction de post-traitement (après get).
    acces = init_acces()

    @staticmethod
    def init_acces():
        "Crée le dictionnaire d'accès"

        res = {
            'Nom'                   : {'query' : 'nom'},
            'Prénom'                : {'query' : 'prénom'},
            'Sexe'                  : {'query' : 'sexe'},
            'Date de naissance'     : {'query' : 'naissance',
                                       'default': '01/01/1970'}, # EPOCH!
            'Classe actuelle'       : {'query' : 'synoptique/classe'},
            'Num ParcoursSup'       : {'query' : 'id_apb'},
            'INE'                   : {'query' : 'INE'},
            'Nationalité'           : {'query' : 'nationalité'},
            'Boursier'              : {'query' : 'boursier'},
            'Boursier certifié'     : {'query' : 'boursier_certifie'},
            'Établissement'         : {'query' : 'synoptique/établissement/nom'},
            'Commune'               : {'query' : 'synoptique/établissement/ville'},
            'Département'           : {'query' : 'synoptique/établissement/département'},
            'Pays'                  : {'query' : 'synoptique/établissement/pays'},
            'Écrit EAF'             : {'query' : 'synoptique/français.écrit',
                                       'default' : '-',
                                       'pre' : normalize_note,
                                       'post' : format_mark},
            'Oral EAF'              : {'query' : 'synoptique/français.oral',
                                       'default' : '-',
                                       'pre' : normalize_note,
                                       'post' : format_mark},
            'Candidatures'          : {'query' : 'diagnostic/candidatures',
                                       'pre' : format_candidatures},
            'Candidatures impr'     : {'query' : 'diagnostic/candidatures',
                                       'post' : format_candidatures_impr},
            'Première semestrielle' : {'query' : 'bulletins/bulletin[classe="Première"]/semestriel',
                                       'default' : '0'},
            'Terminale semestrielle': {'query' : 'bulletins/bulletin[classe="Terminale"]/semestriel',
                                       'default' : '0'},
            'traité'                : {'query' : 'diagnostic/traité',
                                       'default' : False},
            'Jury'                  : {'query' : 'diagnostic/jury',
                                       'default' : 'Auto',
                                       'pre' : format_jury},
            'Motifs'                : {'query' : 'diagnostic/motifs',
                                       'default' : ''},
            'Score brut'            : {'query' : 'diagnostic/score',
                                       'default' : ''},
            'Correction'            : {'query' : 'diagnostic/correc',
                                       'default' : '0'},
            'Score final'           : {'query' : 'diagnostic/scoref',
                                       'default' : ''},
            'Rang brut'             : {'query' : 'diagnostic/rangb'},
            'Rang final'            : {'query' : 'diagnostic/rangf'},
        }

        for val in res.values():
            if not 'default' in val:
                val['default'] = '?'

        return res

    # Pour les notes du lycée :
    matiere = ['Mathématiques',
               'Mathématiques Spécialité',
               'Mathématiques Expertes',
               'Physique/Chimie',
               'Physique-Chimie Spécialité']
    date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
    classe = ['Première', 'Terminale']
    for cl in classe:
        for mat in matiere:
            for da in date:
                key = '{} {} {}'.format(mat, cl, da)
                query_classe = f'bulletins/bulletin[classe="{cl}"]'
                query_mat = f'{query_classe}/matières/matière[intitulé="{mat}"]'
                query = f'{query_mat}[date="{da}"]/note'
                acces[key] = {'query' : query,
                              'default' : '-',
                              'pre' : normalize_note,
                              'post' : format_mark}
    # Pour les notes CPES :
    for mat in matiere:
        key = '{} CPES'.format(mat)
        query = 'synoptique/matières/matière[intitulé="{}"]/note'.format(mat)
        acces[key] = {'query' : query, 'default' : '-', 'pre' : normalize_note, 'post' : format_mark}
    ############## Fin attributs de classe ########

    ############# Méthodes d'instance #############
    #                                             #
    def __init__(self, nom):
        """ Constructeur d'une instance Fichier.
        'nom' est le chemin d'un fichier xml. """
        # stockage du nom
        self.nom = nom
        # A priori, il n'est pas nécessaire de vérifier que le
        # fichier 'nom' existe, cela a été fait avant la construction
        parser = etree.XMLParser(remove_blank_text=True) # pour que pretty_print fonctionne bien
        self._dossiers = etree.parse(nom, parser).getroot() # récupération du contenu du fichier
        # On créé aussi l'ensemble (set) des identifiants des candidats
        self._identif = {Fichier.get(cand, 'Num ParcoursSup') for cand in self._dossiers}
        # On récupère la filière. Utilisation d'un set pour éviter les doublons !
        self._filiere = {fil for fil in filieres if fil in nom.lower()}.pop()

    def __iter__(self):
        """ Cette méthode fait d'un objet fichier un itérable (utilisable dans une boucle)
        Cela sert à créer la liste de dossiers qui apparaît dans la page html de traitement
        On itère sur la liste de dossiers que contient le fichier. """
        return self._dossiers.__iter__()

    def __contains__(self, cand):
        """ méthode qui implémente l'opérateur 'in'.
        la syntaxe est 'if cand in objet_Fichier'
        dans laquelle cand est un noeud xml pointant sur un candidat.
        Elle retourne un booléen. Utile pour l'admin qui traite un
        candidat et reporte dans toutes les filières demandées. """
        return Fichier.get(cand, 'Num ParcoursSup') in self._identif

    def __len__(self):
        """ Cette méthode confère un sens à l'opération len(fichier) """
        return len(self._dossiers)

    def cand(self, index):
        """ Renvoie le noeud candidat indexé par 'index' dans self._dossiers """
        return self._dossiers[index]

    def get_cand(self, cand):
        """ Renvoie le candidat dont l'identifiant est identique à celui de cand """
        # Sert à l'admin quand il traite un candidat sur une filière
        # et REPORTE ses modifs dans toutes les filières demandées..
        # Sert aussi à la fonction stat() dans la classe Admin.
        # À n'utiliser que sur des fichiers contenant le candidat ('cand in fichier' True)
        # Utile de la rendre plus robuste (gérer l'erreur si 'cand in fichier' False) ?
        index = 0
        fich_cand = Fichier.get(cand, 'Num ParcoursSup')
        while fich_cand != Fichier.get(self._dossiers[index], 'Num ParcoursSup'):
            index += 1
        return self._dossiers[index]

    def filiere(self):
        """ renvoie la filière """
        return self._filiere

    def ordonne(self, critere):
        """ renvoie une liste des candidatures ordonnées selon le critère demandé
        (critère appartenant à l'attribut de classe _critere_tri) """
        # Classement par age
        tri = lambda cand: date_to_num(Fichier.get(cand, 'Date de naissance'))
        doss = sorted(self._dossiers, key = tri)
        # puis par critere
        return sorted(doss, key = Fichier._criteres_tri[critere])

    def sauvegarde(self):
        """ Sauvegarde le fichier : mise à jour (par écrasement) du fichier xml """
        with open(self.nom, 'wb') as fich:
            fich.write(etree.tostring(self._dossiers, pretty_print=True, encoding='utf-8'))
