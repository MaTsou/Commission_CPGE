#-*- coding: utf-8 -*-
# pylint: disable=I1101
# I1101 car lxml le déclenche beaucoup

"""Ce module fournit la classe Candidat, qui décrit le dossier d'un
candidat sous une forme facilement interrogeable.

"""

# Le dictionnaire 'acces' contient le chemin xpath relatif à
# l'attribut attr et éventuellement le nom d'une fonction de
# post-traitement. Celle-ci sert à mettre en 'forme' la valeur
# lue (nécessairement de type string) pour l'usage auquel elle
# est destinée. 'acces' contient également la valeur à
# renvoyer dans le cas où le noeud n'existe pas (valeur par
# défaut).

from enum import IntEnum, auto
from parse import parse
from lxml import etree
import logging
from utils.parametres import coef_cpes, coef_term
from utils.toolbox import (date_to_num, str_to_num, normalize_mark,
                           format_candidatures, format_candidatures_impr,
                           format_jury, format_rank)

## _acces : dictionnaire contenant les clés d'accès aux informations candidat
# L'argument est encore un dictionnaire :
# Celui-ci DOIT contenir :
#       une clé 'query' donnant le path xml,
#       une clé 'default' donnant la valeur à renvoyer par défaut.
# et il PEUT contenir :
#       une clé 'pre' donnant une fonction de pré-traitement (avant set),
#       une clé 'post' donnant une fonction de post-traitement (après get).

def _init_acces():
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
        'Département'           : {'query' : \
                'synoptique/établissement/département'},
        'Pays'                  : {'query' : 'synoptique/établissement/pays'},
        'Écrit EAF'             : {'query' : 'synoptique/français.écrit',
                                   'default' : '-',
                                   'pre' : normalize_mark,
                                   'post' : str_to_num},
        'Oral EAF'              : {'query' : 'synoptique/français.oral',
                                   'default' : '-',
                                   'pre' : normalize_mark,
                                   'post' : str_to_num},
        'Candidatures'          : {'query' : 'diagnostic/candidatures',
                                   'pre' : format_candidatures},
        'Candidatures impr'     : {'query' : 'diagnostic/candidatures',
                                   'post' : format_candidatures_impr},
        'Première semestrielle' : {'query' : \
                'bulletins/bulletin[classe="Première"]/semestriel',
                                   'default' : '0'},
        'Terminale semestrielle': {'query' : \
                'bulletins/bulletin[classe="Terminale"]/semestriel',
                                   'default' : '0'},
        'traité'                : {'query' : 'diagnostic/traité',
                                   'default' : False},
        'Jury'                  : {'query' : 'diagnostic/jury',
                                   'default' : 'Auto',
                                   'pre' : format_jury},
        'Motifs'                : {'query' : 'diagnostic/motifs',
                                   'default' : ''},
        'Score brut'            : {'query' : 'diagnostic/score',
                                   'default' : '0.0',
                                   'pre' : str,
                                   'post' : str_to_num},
        'Correction'            : {'query' : 'diagnostic/correc',
                                   'default' : '0',
                                   'pre' : str,
                                   'post' : str_to_num},
        'Score final'           : {'query' : 'diagnostic/scoref',
                                   'default' : '0.0',
                                   'pre' : str,
                                   'post' : str_to_num},
        'Rang brut'             : {'query' : 'diagnostic/rangb',
                                   'pre' : str,
                                   'post' : format_rank},
        'Rang final'            : {'query' : 'diagnostic/rangf',
                                   'pre' : str,
                                   'post' : format_rank},
    }

    # On garantit qu'une valeur par défaut existe
    for val in res.values():
        if not 'default' in val.keys():
            val['default'] = '?'

    # Pour les notes du lycée :
    matieres = ['Mathématiques',
                'Mathématiques Spécialité',
                'Mathématiques Expertes',
                'Physique/Chimie',
                'Physique-Chimie Spécialité',
                'Français']
    dates = ['trimestre 1', 'trimestre 2', 'trimestre 3']
    classes = ['Première', 'Terminale']
    for classe in classes:
        for matiere in matieres:
            for date in dates:
                key = f'{matiere} {classe} {date}'
                query_classe = f'bulletins/bulletin[classe="{classe}"]'
                query_matiere = \
                        f'{query_classe}/matières/matière[intitulé="{matiere}"]'
                query = f'{query_matiere}[date="{date}"]/note'
                res[key] = {'query' : query,
                            'default' : '-',
                            'pre' : normalize_mark,
                            'post' : str_to_num}
    # Pour les notes CPES :
    for matiere in matieres:
        key = f'{matiere} CPES'
        query = f'synoptique/matières/matière[intitulé="{matiere}"]/note'
        res[key] = {'query' : query,
                    'default' : '-',
                    'pre' : normalize_mark,
                    'post' : str_to_num}

    return res

_acces = _init_acces()

class Candidat:
    """Le but de ce type d'objet est de fournir une interface sur un nœud
    XML décrivant un candidat"""

    def __init__(self, node):
        self._node = node
        self.journal = logging.getLogger('commission')
        self._coefs = {}
        self.set_coefs()

    def get_node(self):
        return self._node

    def get(self, attr):
        """accesseur : récupère l'information voulue sur le candidat ; attr
        est une clef du dictionnaire '_acces'

        """

        my_attr = _acces[attr]
        try:
            result = self._node.xpath(my_attr['query'])[0].text
        except:
            result = None
        if not result:
            result = my_attr['default'] # init_acces garantit que ça marche

        if 'post' in my_attr:
            result = my_attr['post'](result)

# ATTENTION : une écriture dans le journal ici cause une erreur. De ce que j'ai 
# compris, la bibliothèque logger utilise des threads. La méthode get étant 
# appelée très souvent, ça plante : trop de threads simultanés.
        if 'score' in attr.lower():
            self.journal.debug(f"{self.get('Nom')} {self.get('Prénom')} : get( {attr} ) a renvoyé {result} de type {type(result)}")
        return result

    def set(self, attr, value):
        """mutateur : écrit l'information voulue sur le candidat ; attr est
        une clef du dictionnaire '_acces'. Si le sous-nœud cible
        n'existe pas, il est créé."""

        # '_acces' contient éventuellement une le nom d'une fonction
        # de pré-traitement. Celle-ci sert à préparer la valeur à
        # être stockée dans le fichier XML.
        my_attr = _acces[attr]
        query = my_attr['query']
        if 'pre' in my_attr:
            value = my_attr['pre'](value)
        self.journal.debug(f"{self.get('Nom')} {self.get('Prénom')} : set( ) tente d'attribuer ({value} de type {type(value)} à l'attribut {attr}")
        try:
            self._node.xpath(query)[0].text = value
        except:
            self.journal.debug(f"Candidat {self.get('Nom')} {self.get('Prénom')} : le noeud {query} n'existe pas; lancement de _accro_branche.")
            node = query.split('/')[-1]
            fils = etree.Element(node)
            fils.text = value
            pere = parse('{}/' + node, query)[0]
            self._accro_branche(pere, fils)

    def _accro_branche(self, pere, fils):
        """Reconstruction d'une arborescence incomplète. On procède de manière
        récursive en commençant par l'extrémité (les feuilles !)...
        pere est un chemin (xpath) et fils un etree.Element

        ATTENTION : il ne faut pas d'espaces superflues dans la chaine
        pere.

        """

        if self._node.xpath(pere) != []: # test si pere est une branche existante
            self._node.xpath(pere)[0].append(fils) # si oui, on accroche le fils
        else: # sinon on créé le père et on va voir le grand-père

            # récupération du dernier champ du chemin
            node = pere.split('/')[-1]

             # un traitement particulier quand le champ contient (Physique/Chimie)
            if node.startswith('Chimie'):
                node=pere.split('/')[-2]+'/'+node
            # le reste du chemin est le grand-pere
            grand_pere = parse('{}/' + node, pere)[0]
            # analyse et création du père avec tous ses champs...
            noeuds = parse('{}[{}]', node)
            if noeuds is None:
                noeuds = [node]
            pere = etree.Element(noeuds[0])
            if noeuds != [node]: # le père a d'autres enfants
                for li in noeuds[1].split(']['):
                    dico = parse('{nom}="{val}"', li)
                    element = etree.Element(dico['nom'])
                    element.text = dico['val']
                    pere.append(element)
            pere.append(fils)
            self._accro_branche(grand_pere, pere)

    def identifiant(self):
        """Renvoie le numéro d'identifiant sur ParcoursSup"""
        return self.get('Num ParcoursSup')

    def set_coefs(self):
        # Récupération des coefficients, en les copiant car si
        # l'organisation est semestrielle, on va vouloir faire des
        # reports pour maintenir les poids relatifs
        if self.is_cpes():
            self._coefs = dict(coef_cpes)
            # report coef de terminale si notation semestrielle
            if self.is_terminale_semestrielle():
                for key, val in self._coefs.items():
                    if 'Terminale trimestre 3' in key:
                        self._coefs[key.replace('trimestre 3', \
                                'trimestre 1')] += val/2
                        self._coefs[key.replace('trimestre 3', \
                                'trimestre 2')] += val/2
                        self._coefs[key] = 0
        else:
            self._coefs = dict(coef_term)
            # report coef de terminale si notation semestrielle
            if self.is_terminale_semestrielle():
                for key, val in self._coefs.items():
                    if 'Terminale trimestre 2' in key:
                        self._coefs[key.replace('trimestre 2', \
                                'trimestre 1')] += val
                        self._coefs[key] = 0

        # Report des coef de première si notation semestrielle
        if self.is_premiere_semestrielle():
            for key, val in self._coefs.items():
                if 'Première trimestre 3' in key:
                    self._coefs[key.replace('trimestre 3', \
                            'trimestre 1')] += val/2
                    self._coefs[key.replace('trimestre 3', \
                            'trimestre 2')] += val/2
                    self._coefs[key] = 0

        # Il y a aussi des reports si le candidat ne suit pas l'option math 
        # expertes
        if not self.is_math_expertes():
            for key,val in self._coefs.items():
                if 'Expertes' in key:
                    self._coefs[key.replace('Expertes', 'Spécialité')] += val
                    self._coefs[key] = 0

        #####################################
        # Reports spécial-confinement FIXME : à supprimer complètement à terme
        # self.coef_confinement()
        #####################################

    def coef_confinement(self):
        if self.is_cpes():
            # report coef de terminale si notation semestrielle
            if self.is_terminale_semestrielle():
                for key, val in self._coefs.items():
                    if 'Terminale trimestre 2' in key:
                        self._coefs[key.replace('trimestre 2', \
                                'trimestre 1')] += val
                        self._coefs[key] = 0
            else:
                for key, val in self._coefs.items():
                    if 'Terminale trimestre 3' in key:
                        self._coefs[key.replace('trimestre 3', \
                                'trimestre 1')] += val/2
                        self._coefs[key.replace('trimestre 3', \
                                'trimestre 2')] += val/2
                        self._coefs[key] = 0
        else:
            # report coef de première si notation semestrielle
            if self.is_premiere_semestrielle():
                for key, val in self._coefs.items():
                    if 'Première trimestre 2' in key:
                        self._coefs[key.replace('trimestre 2', \
                                'trimestre 1')] += val
                        self._coefs[key] = 0
            else:
                for key, val in self._coefs.items():
                    if 'Première trimestre 3' in key:
                        self._coefs[key.replace('trimestre 3', \
                                'trimestre 1')] += val/2
                        self._coefs[key.replace('trimestre 3', \
                                'trimestre 2')] += val/2
                        self._coefs[key] = 0

    def is_cpes(self):
        """Renvoie True si le candidat est en CPES """
        return 'cpes' in self.get('Classe actuelle').lower()

    def is_math_expertes(self):
        """Renvoie True si le candidat a au moins une note d'option math
        expertes

        """

        expert = False # initialisation
        # Construction de l'ensemble des champs à vérifier
        champs = {f"Mathématiques Expertes Terminale trimestre {j}" \
                for j in range(1,4)}

        # Dès qu'un champ est renseigné on arrête et renvoie True
        while len(champs) > 0:
            champ = champs.pop()
            if self.get(champ) != _acces[champ]['default']: # champ renseigné ?
                expert = True
                break
        return expert

    def is_premiere_semestrielle(self):
        """Renvoie True si le candidat est noté en semestres en première

        """
        return self.get('Première semestrielle') == '1'

    def is_terminale_semestrielle(self):
        """Renvoie True si le candidat est noté en semestres en terminale

        """
        return self.get('Terminale semestrielle') == '1'

    def is_complet(self):
        """Renvoie True si tous les éléments nécessaires à un calcul correct
        du score brut sont présents"""

        # Cette fonction est appelée dans nettoie.py. Si elle renvoie
        # False, une alerte est mise en place et l'admin doit faire
        # tout ce qu'il peut pour la lever..  Les éléments à vérifier
        # sont lus dans parametres.py (coef...)

        # Initialisation des coefs
        self.set_coefs()

        # Construction de l'ensemble des champs à vérifier :
        # toutes les notes affectées d'un coef non nul
        champs = set([key for key in self._coefs.keys() \
                if self._coefs[key]])

        # Tests :
        complet = not self.get('Classe actuelle') == \
                _acces['Classe actuelle']['default']

        # Dès qu'un champ manque à l'appel on arrête et renvoie False
        while complet and len(champs) > 0:
            champ = champs.pop()
            if self.get(champ) == _acces[champ]['default']: # note absente ?
                complet = False
        return complet

    def update_raw_score(self):
        """ Calcul du score brut et mise à jour dans le nœud XML """

        # Si correction = 'NC', cela signifie que l'admin rejette le
        # dossier ; score nul d'office!
        if self.get('Correction') == 'NC': # candidat rejeté
            self.set('Score brut', 0)
            return

        # Mise à jour des coefs (cas d'un dossier complété par admin)
        self.set_coefs()
        # On a maintenant tout ce qu'il faut pour lancer le calcul
        somme, poids = 0, 0
        for key, val in self._coefs.items():
            note = self.get(key)
            if note != _acces[key]['default']:
                somme += note*val
                poids += val
        if poids != 0:
            scoreb = somme/poids
        else: # ne devrait pas arriver
            scoreb = 0
        # Bonus pour les cpes ou les math expertes...
        if (self.is_cpes() or self.is_math_expertes()):
            scoreb += 5
        self.set('Score brut', scoreb)

    class Critere(IntEnum):
        """Fournit la liste des critères de score possibles pour un candidat"""

        SCORE_BRUT = auto()

        SCORE_FINAL = auto()

        NOM = auto()

        NAISSANCE = auto()

    def score(self, critere = Critere.SCORE_BRUT):
        """Renvoie le score du candidat suivant le critère demandé
        """

        if critere == Candidat.Critere.SCORE_BRUT:
            return -self.get('Score brut')
        if critere == Candidat.Critere.SCORE_FINAL:
            return -self.get('Score final')
        if critere == Candidat.Critere.NOM:
            return self.get('Nom')
        if critere == Candidat.Critere.NAISSANCE:
            return -date_to_num(self.get('Date de naissance'))
        return 0
