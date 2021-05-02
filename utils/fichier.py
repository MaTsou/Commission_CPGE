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

from lxml import etree
import logging
from utils.candidat import Candidat
from config import filieres

#################################################################################
#                               Fichier                                         #
#################################################################################
class Fichier:
    """objet fichier : son but est de contenir toutes les méthodes qui
    agissent sur le contenu des fichiers, i.e. les dossiers de
    candidatures. Ces fichiers sont des attributs des objets 'Client'
    que gère l'objet 'Serveur'.

    """

    ############# Méthodes d'instance #############
    #                                             #
    def __init__(self, nom):
        """ Constructeur d'une instance Fichier.
        'nom' est le chemin d'un fichier xml. """

        # stockage du nom et du journal
        self.nom = nom
        self.journal = logging.getLogger('commission')

        # A priori, il n'est pas nécessaire de vérifier que le fichier 'nom'
        # existe, cela a été fait avant la construction

        # Ci-dessous, option remove_blank pour que pretty_print fonctionne bien
        parser = etree.XMLParser(remove_blank_text=True)

        # récupération du contenu du fichier :
        self._root = etree.parse(nom, parser).getroot()
        self._candidats = [Candidat(node) \
                for node in self._root.xpath('candidat')]

        # On créé aussi l'ensemble (set) des identifiants des
        # candidats pour que __contains__ soit plus efficace
        self._identif = {candidat.identifiant() for candidat in self._candidats}

        # On récupère la filière. Utilisation d'un set pour éviter les doublons !
        self._filiere = {fil for fil in filieres if fil in nom.lower()}.pop()

    def __iter__(self):
        """ Cette méthode fait d'un objet fichier un itérable (utilisable dans
        une boucle) Cela sert à créer la liste de dossiers qui apparaît dans la
        page html de traitement On itère sur la liste de dossiers que contient
        le fichier. """
        return self._candidats.__iter__()

    def __contains__(self, candidat_):
        """ méthode qui implémente l'opérateur 'in'.  la syntaxe est 'if cand in
        objet_Fichier' dans laquelle cand est un noeud xml pointant sur un
        candidat.  Elle retourne un booléen. Utile pour l'admin qui traite un
        candidat et reporte dans toutes les filières demandées. """
        return candidat_.identifiant() in self._identif

    def __len__(self):
        """ Cette méthode confère un sens à l'opération len(fichier) """
        return len(self._candidats)

    def cand(self, index):
        """ Renvoie le noeud candidat indexé par 'index' dans self._dossiers """
        return self._candidats[index]

    def get_cand(self, candidat):
        """ Renvoie le candidat dont l'identifiant est identique à celui de cand
        """
        # Sert à l'admin quand il traite un candidat sur une filière et REPORTE
        # ses modifs dans toutes les filières demandées..  Sert aussi à la
        # fonction stat() dans la classe Admin.  À n'utiliser que sur des
        # fichiers contenant le candidat ('cand in fichier' True) Utile de la
        # rendre plus robuste (gérer l'erreur si 'cand in fichier' False) ?
        index = 0
        num = candidat.identifiant()
        while num != self._candidats[index].identifiant():
            index += 1
        return self._candidats[index]

    def filiere(self):
        """ renvoie la filière """
        return self._filiere

    Critere = Candidat.Critere

    def ordonne(self, critere = Critere.SCORE_BRUT):
        """renvoie une liste des candidatures ordonnées selon le critère donné
        -- mais après avoir trié par âge, donc en privilégiant les
        plus jeunes.

        """

        candidats = sorted(self._candidats, \
                key = lambda cand: Fichier.Critere.NAISSANCE)
        candidats.sort(key = lambda cand: cand.score(critere))
        return candidats

    def sauvegarde(self):
        """ Sauvegarde le fichier : mise à jour (par écrasement) du fichier xml
        """
        with open(self.nom, 'wb') as fich:
            fich.write(etree.tostring(self._root, pretty_print=True, \
                    encoding='utf-8'))
