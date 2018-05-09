#!/usr/bin/env python3
#-*- coding: utf-8 -*-

# Ce fichier contient la classe Client (du serveur) et les classes
# dérivées (Admin et Jury)
###
# 1/ Classe Client :
#   Classe 'générique', n'est pas utilisée en tant que telle mais
#   sert de classe mère aux classes Jury et Admin. Elle est le
#   prototype des objets qui se connectent au serveur.
# 2/ Classe Jury :
#   Client de type 'jury' de commission.
# 3/ Classe Admin :
#   Client de type 'administrateur' de commission.
###

import os, glob, pickle
from parse import parse
from utils.parametres import nb_jurys
from utils.fichier import Fichier

#################################################################################
#                               Class Client                                    #
#################################################################################

class Client(): 
    """ Objet client "abstrait" pour la class Serveur """
    def __init__(self, key, droits):
        """ constructeur """
        # identifiant du client : contenu du cookie déposé sur la machine client
        self.je_suis = key  
        self._droits = droits  # droits : admin ou jury... Attribut privé car méthode set particulière..
        self.fichier = None  # contiendra une instance 'Fichier'
        # Index (dans le fichier) du candidat suivi.
        self.num_doss = -1  # -1 signifie : le jury n'est pas en cours de traitement
    
    def get_droits(self):
        return self._droits

    def get_cand(self) :
        """ renvoie le candidat courant """
        return self.fichier.cand(self.num_doss)
        
    def set_fichier(self, fich):
        self.fichier = fich
        r = parse('{}_{}.xml', fich.nom) # récupère nom de la filière traitée
        self._droits += ' {}'.format(r[1])
        self.num_doss = 0 # on commence par le premier !

#################################################################################
#                               Class Jury                                      #
#################################################################################

class Jury(Client): 
    """  Objet client (de type jury de commission) pour la class Serveur """
    def __init__(self, key):
        """ constructeur : on créé une instance Client avec droits "jury" """
        Client.__init__(self, key, 'Jury')
        # Fichiers javascripts
        self.script_menu = 'utils/scripts/menu_jury.js'
        self.script_dossiers = 'utils/scripts/dossiers_jury.js'

    def set_droits(self, droits):
        self._droits = 'Jury' + droits

    def get_rgfinal(self, cand):
        """ Estimation du rg final d'un candidat """
        # On récupère les dossiers traités seulement
        doss = [ca for ca in self.fichier if (Fichier.get(ca, 'traité') == 'oui' and Fichier.get(ca, 'Correction') != 'NC')]
        # Ceux-ci sont classés par ordre de score final décroissant
        doss[:] = sorted(doss, key = lambda cand: -Fichier.get(cand, 'Score final num'))
        # On calcule le rang du score_final actuel (celui de cand) dans cette liste
        rg = Fichier.rang(cand, doss, 'Score final num')
        # À ce stade, rg est le rang dans la liste du jury. 
        # La suite consiste à calculer n*(rg-1) + k
        # où n est le nombre de jurys et k l'indice du jury courant.
        q = parse('Jury {:w}{:d}', self._droits)
        n = int(nb_jurys[q[0].lower()])
        k = int(q[1])
        return n*(rg-1)+k

    def traiter(self, **kwargs):
        """ Traiter un dossier """
        # Fonction lancée par la fonction "traiter" du Serveur. Elle même est lancée par validation d'un dossier
        # On récupère le candidat
        cand  = self.get_cand()
        ## On met à jour le contenu de ce dossier :
        # 1/ correction apportée par le jury et score final
        if kwargs['nc'] == 'NC':
            cor, scoref = 'NC', 'NC'
        else:
            cor = kwargs['correc']
            note = float(Fichier.get(cand, 'Score brut').replace(',','.')) + float(cor)
            scoref = '{:.2f}'.format(note).replace('.',',')
        Fichier.set(cand, 'Correction', cor)
        Fichier.set(cand, 'Score final', scoref)
        # 2/ Qui a traité le dossier
        Fichier.set(cand, 'Jury', self._droits)
        # 2bis/ On met à jour le fichier des décomptes de commission
        if (not(Fichier.get(cand, 'traité')) and cor != 'NC'): # seulement si le candidat n'a pas déjà été vu et si classé!
            with open(os.path.join(os.curdir,"data","decomptes"), 'br') as fich:
                decompt = pickle.load(fich)
            qui = self._droits
            for key in decompt.keys():
                if key in qui:
                    decompt[key] += 1
            with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') as stat_fich:
                pickle.dump(decompt, stat_fich)
        # 3/ "bouléen" traite : le dossier a été traité (classé ou non classé)
        Fichier.set(cand, 'traité', 'oui')
        # 4/ motivation du jury
        Fichier.set(cand, 'Motifs', kwargs['motif'])
        ## Fin mise à jour dossier
        # On sélectionne le dossier suivant
        if self.num_doss < len(self.fichier)-1:
            self.num_doss += 1
        # Et on sauvegarde le tout
        self.fichier.sauvegarde()

#################################################################################
#                               Class Admin                                     #
#################################################################################
class Admin(Client): 
    """ Objet client (de type Administrateur) pour la class Serveur """
    def __init__(self, key): 
        """ constructeur : on créé une instance Client avec droits "admin" """
        Client.__init__(self, key, 'Administrateur')
        # Fichiers javascripts
        self.script_menu = 'utils/scripts/menu_admin.js'
        self.script_dossiers = 'utils/scripts/dossiers_admin.js'
    
    def set_droits(self, droits):
        self._droits = 'Administrateur' + droits

    def traiter(self, **kwargs):
        """ Traiter un dossier """
        # On récupère le candidat courant
        cand = self.get_cand()
        # Ici, on va répercuter les complétions de l'administrateur dans tous les dossiers que le
        # candidat a déposé.
        # Attention ! le traitement du fichier en cours est fait à part car deux objets 'Fichier' qui
        # auraient le même nom sont malgré tout différents !! On rajoute la bonne instance Fichier juste après.
        # Recherche de tous les fichiers existants :
        list_fich_admin = [Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))\
                if fich != self.fichier.nom]
        # On restreint la liste aux fichiers contenant le candidat en cours
        list_fich_cand = [fich for fich in list_fich_admin if cand in fich]
        # On rajoute le fichier suivi actuellement
        list_fich_cand.append(self.fichier)
        ############### Admin a-t-il changé qqc ? Si oui, mise à jour. 
        # Classe actuelle ?
        if Fichier.get(cand, 'Classe actuelle') != kwargs['Classe actuelle']:
            for fich in list_fich_cand: Fichier.set(fich.get_cand(cand), 'Classe actuelle', kwargs['Classe actuelle'])
            # semestres ?
        txt = kwargs.get('sem_prem','off')  # kwargs ne contient 'sem_prem' que si la case est cochée !
        for fich in list_fich_cand: Fichier.set(fich.get_cand(cand), 'sem_prem', txt)
        txt = kwargs.get('sem_term','off')  # kwargs ne contient 'sem_term' que si la case est cochée !
        for fich in list_fich_cand: Fichier.set(fich.get_cand(cand), 'sem_term', txt)
            # Cas des notes
        matiere = ['Mathématiques', 'Physique/Chimie']
        date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
        classe = ['Première', 'Terminale']
        for cl in classe:
            for mat in matiere:
                for da in date:
                    key_script = '{}{}{}'.format(cl[0], mat[0], da[-1])
                    key = '{} {} {}'.format(mat, cl, da)
                    if Fichier.get(cand, key) != kwargs[key_script]:
                        for fich in list_fich_cand: Fichier.set(fich.get_cand(cand), key, kwargs[key_script])
            # CPES
        liste = ['Mathématiques CPES', 'Physique/Chimie CPES', 'Écrit EAF', 'Oral EAF']
        for li in liste:
            if 'cpes' in li.lower():
                if ('cpes' in Fichier.get(cand, 'Classe actuelle').lower()) and Fichier.get(cand, li) != kwargs[li]:
                    for fich in list_fich_cand: Fichier.set(fich.get_cand(cand), li, kwargs[li])
            else:
                if Fichier.get(cand, li) != kwargs[li]:
                    for fich in list_fich_cand: Fichier.set(fich.get_cand(cand), li, kwargs[li])
        # On (re)calcule le score brut !
        Fichier.calcul_scoreb(cand)
        # Commentaire éventuel admin + gestion des 'NC'
        # Les commentaires admin sont précédés de '- Admin :' c'est à cela qu'on les reconnaît
        # Notamment, script.js exclut qu'un tel commentaires soit considéré comme une motivation
        # de jury.
        motif = kwargs['motif']
        if not('- Admin :' in motif or motif == ''):
            motif = '- Admin : {}'.format(motif)
        if kwargs['nc'] == 'NC':
            # L'admin a validé le formulaire avec le bouton NC (le candidat ne passera pas en commission)
            # Pour ce cas là, on ne recopie pas dans toutes les filières. Admin peut exclure une candidature
            # dans une filière sans l'exclure des autres. Sécurité !
            Fichier.set(cand, 'Correction', 'NC') # la fonction calcul_scoreb renverra 0 !
            Fichier.set(cand, 'Jury', 'Admin')
            Fichier.set(self.fichier.get_cand(cand), 'Motifs', motif)
        else:
            for fich in list_fich_cand:
                Fichier.set(fich.get_cand(cand), 'Correction', '0')
                Fichier.set(fich.get_cand(cand), 'Motifs', motif)

        # On sauvegarde tous les fichiers retouchés
        for fich in list_fich_cand:
            fich.sauvegarde()
