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

import os, glob, pickle, copy, csv
from lxml import etree
from parse import parse
from utils.fichier import Fichier
from utils.csv_parcourssup import lire
from utils.nettoie_xml import nettoie
from config import filieres, nb_jurys, nb_classes, tableaux_candidats_classes, tableaux_tous_candidats
from utils.toolbox import decoup, restaure_virginite

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
        doss[:] = sorted(doss, key = lambda cand: -float(Fichier.get(cand, 'Score final').replace(',','.')))
        # On calcule le rang du score_final actuel (celui de cand) dans cette liste
        rg = Fichier.rang(cand, doss, 'Score final')
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
            cor, scoref = 'NC', '0'
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

    def traiter_csv(self):
        yield "     Début du traitement des fichiers csv\n"
        for source in glob.glob(os.path.join(os.curdir, "data", "*.csv")):
            for fil in filieres:
                if fil in source.lower(): # Attention le fichier csv doit contenir la filière...
                    dest = os.path.join(os.curdir, "data", "admin_{}.xml".format(fil.upper()))
                    yield "         Fichier {} ... ".format(fil.upper())
                    contenu_xml = lire(source) # première lecture brute
                    contenu_xml = nettoie(contenu_xml) # nettoyage doux
                    with open(dest, 'wb') as fich:
                        fich.write(etree.tostring(contenu_xml, pretty_print=True, encoding='utf-8'))
                    yield "traité.\n"

    def traiter_pdf(self):
        yield "\n     Début du traitement des fichiers pdf (traitement long, restez patient...)\n"
        dest = os.path.join(os.curdir, "data", "docs_candidats")
        restaure_virginite(dest) # un coup de jeune pour dest..
        for fich in glob.glob(os.path.join(os.curdir, "data", "*.pdf")):
            for fil in filieres:
                if fil in fich.lower():
                    yield "         Fichier {} ... ".format(fil.upper())
                    desti = os.path.join(dest, fil)
                    os.mkdir(desti)
                    decoup(fich, desti) # fonction de découpage du pdf
                    yield "traité.\n".format(parse("{}_{4s}.pdf", fich)[1])

    def stat(self, list_fich):
        """ Effectue des statistiques sur les candidats """
        # On ordonne selon l'ordre spécifié dans filieres (parametres.py)
        list_fich = sorted(list_fich, key = lambda f: filieres.index(f.filiere().lower()))
        # L'info de candidatures est stockée dans un nombre binaire où 1 bit 
        # correspond à 1 filière. Un dictionnaire 'candid' admet ces nombres binaires pour clés,
        # et les valeurs sont des nombres de candidats. 
        # candid = {'001' : 609, '011' : 245, ...} indique que 609 candidats ont demandé
        # le filière 1 et 245 ont demandé à la fois la filière 1 et la filière 2

        # Initialisation du dictionnaire stockant toutes les candidatures
        candid = {i : 0 for i in range(2**len(filieres))}

        # Recherche des candidatures # je suis très fier de cet algorithme !!
        # Construction des éléments de recherche
        l_dict = [ {Fichier.get(cand, 'Num ParcoursSup') : cand for cand in fich} for fich in list_fich ] # liste de dicos
        l_set = [ set(d.keys()) for d in l_dict ] # list d'ensembles (set())
        # Création des statistiques
        for (k,n) in enumerate(l_set):
            while len(n) > 0:
                a = n.pop()
                cc, liste = 2**k, [k]
                for i in range(k+1, len(list_fich)):
                    if a in l_set[i]:
                        cc |= 2**i
                        l_set[i].remove(a)
                        liste.append(i)
                [Fichier.set(l_dict[j][a], 'Candidatures', cc) for j in liste]
                for j in liste: # le test ci-dessous pourrait exclure les filières inadéquates (bien ou pas ?)..
                    if not('non validée' in Fichier.get(l_dict[j][a], 'Motifs')):
                        candid[2**j]+= 1
                if len(liste) > 1:
                    candid[cc] += 1
        # Sauvegarder
        [fich.sauvegarde() for fich in list_fich]
        
        # Écrire le fichier stat
        with open(os.path.join(os.curdir, "data", "stat"), 'wb') as stat_fich:
            pickle.dump(candid, stat_fich)

    def generation_comm(self):
        """ Création des fichiers commission """
        # Récupération des fichiers admin
        list_fich = [Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))]
        # Pour chaque fichier "admin_*.xml"
        for fich in list_fich:
            # Tout d'abord, calculer le score brut de chaque candidat 
            for cand in fich:
                Fichier.calcul_scoreb(cand)
            # Classement par scoreb décroissant
            doss = fich.ordonne('score_b')
            # Calcul du rang de chaque candidat et renseignement du noeuds 'rang_brut'
            for cand in fich:
                Fichier.set(cand, 'Rang brut',  str(Fichier.rang(cand, doss, 'Score brut')))
            # Récupération de la filière et du nombre de jurys 
            nbjury = int(nb_jurys[fich.filiere().lower()])
            # Découpage en n listes de dossiers
            for j in range(0, nbjury):
                dossier = []    # deepcopy ligne suivante sinon les candidats sont retirés de doss à chaque append
                [dossier.append(copy.deepcopy(doss[i])) for i in range(0, len(doss)) if i%nbjury == j]
                # Sauvegarde
                res = etree.Element('candidats')
                [res.append(cand) for cand in dossier]
                nom = os.path.join(os.curdir, "data", "comm_{}{}.xml".format(fich.filiere().upper(), j+1))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
        # Création fichier decompte
        decompt = {}
        for fil in filieres:
            decompt['{}'.format(fil.upper())]=0
        with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') as stat_fich:
            pickle.dump(decompt, stat_fich)

    def clore_commission(self):
        """ Cloture la commission """
        # Récolter les fichiers après la commission
        # Pour chaque filière
        # Récolte du travail de la commission, mise à jour des scores finals.
        # Classement par ordre de score final décroissant puis réunion des fichiers
        # de chaque sous-commission en un fichier class_XXXX.xml ou XXXX = filière
        # Enfin, création des différents tableaux paramétrés dans paramètres.py
        tot_class = {} # dictionnaire contenant les nombres de candidats classés par filière
        for fil in filieres:
            path = os.path.join(os.curdir, "data", "comm_{}*.xml".format(fil.upper()))
            list_fich = [Fichier(fich) for fich in glob.glob(path)]
            list_doss = [] # contiendra les dossiers de chaque sous-comm
            # Pour chaque sous-commission
            for fich in list_fich:
                # Les fichiers non vus se voient devenir NC avec
                # motifs = "Dossier moins bon que le dernier classé" (sauf s'il y a déjà un motif - Admin)
                for c in fich:
                    if Fichier.get(c, 'traité') != 'oui':
                        Fichier.set(c, 'Correction', 'NC')
                        Fichier.set(c, 'Score final', '0')
                        if Fichier.get(c, 'Motifs') == '':
                            Fichier.set(c, 'Motifs', 'Dossier moins bon que le dernier classé.')
                # list_doss récupère la liste des dossiers classée selon score_final + age
                list_doss.append(fich.ordonne('score_f'))
            # Ensuite, on entremêle les dossiers de chaque sous-comm
            doss_fin = []
            if list_doss: # Y a-t-il des dossiers dans cette liste ?
                nb = len(list_doss[0])
                num = 0
                for i in range(0, nb): # list_doss[0] est le plus grand !!
                    doss_fin.append(list_doss[0][i])
                    for k in range(1, len(list_doss)): # reste-t-il des candidats classés dans les listes suivantes ?
                        if i < len(list_doss[k]): doss_fin.append(list_doss[k][i])
                res = etree.Element('candidats')
                [res.append(c) for c in doss_fin]
                # Rang
                rg = 1
                for cand in res:
                    nu = 'NC'
                    if Fichier.get(cand, 'Correction') != 'NC':
                        nu = str(rg)
                        rg += 1
                    Fichier.set(cand, 'Rang final', nu)
                # Sauvegarde du fichier class...
                nom = os.path.join(os.curdir, "data", "class_{}.xml".format(fil.upper()))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
            tot_class.update({"{}".format(fil.upper()):rg-1})
        # On lance la génération des tableaux bilan de commission
        list_fich = [Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "class_*.xml"))]
        self.tableaux_bilan(list_fich)

    def tableaux_bilan(self, list_fich):
        """ Cette fonction créé les tableaux dont a besoin l'admin pour la suite du recrutement """
        # Un peu de ménage...
        dest = os.path.join(os.curdir, "tableaux")
        restaure_virginite(dest)
        # Pour chaque filière :
        for fich in list_fich:
            # Tableaux candidats classés
            for name in tableaux_candidats_classes.keys():
                # Création du fichier csv
                nom = os.path.join(os.curdir, "tableaux", "{}_{}.csv".format(fich.filiere(), name))
                cw = csv.writer(open(nom, 'w'))
                entetes = tableaux_candidats_classes[name]
                cw.writerow(entetes)
                for cand in fich:
                    a = (Fichier.get(cand, 'traité') == 'oui')
                    b = (Fichier.get(cand, 'Correction') != 'NC')
                    c = not(b) or (int(Fichier.get(cand, 'Rang final')) <= int(nb_classes[fich.filiere().lower()]))
                    if a and b and c: # seulement les classés dont le rang est inférieur à la limite fixée
                        data = [Fichier.get(cand, champ) for champ in entetes]
                        cw.writerow(data)
            # Tableaux tous candidats
            for name in tableaux_tous_candidats:
                # Création du fichier csv
                nom = os.path.join(os.curdir, "tableaux", "{}_{}.csv".format(fich.filiere(), name))
                cw = csv.writer(open(nom, 'w'))
                entetes = tableaux_tous_candidats[name]
                cw.writerow(entetes)
                for cand in fich.ordonne('alpha'):
                    data = [Fichier.get(cand, champ) for champ in entetes]
                    cw.writerow(data)
