#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import os, glob, pickle, copy, csv
from parse import parse
from lxml import etree
from utils.csv_parcourssup import lire
from utils.nettoie_xml import nettoie
from utils.parametres import filieres, nb_jurys, nb_classes, tableaux_candidats_classes, tableaux_tous_candidats
from utils.toolbox import decoup, restaure_virginite
from utils.fichier import Fichier


def traiter_csv():
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

def traiter_pdf():
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

def stat(list_fich):
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

def generation_comm():
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

def clore_commission():
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
                if Fichier.get(c, 'Jury') == 'Auto':
                    Fichier.set(c, 'Correction', 'NC')
                    Fichier.set(c, 'Score final', 'NC')
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
                if Fichier.get(cand, 'Score final') != 'NC':
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
    tableaux_bilan(list_fich)

def tableaux_bilan(list_fich):
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
                b = (Fichier.get(cand, 'Score final') != 'NC')
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
