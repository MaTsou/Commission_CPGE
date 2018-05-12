#!/usr/bin/env python3
#-*- coding: utf-8 -*-

# Ce fichier contient la classe Client et les classes dérivées (Admin et Jury)
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
# Admin et Jury partagent certaines caractéristiques, parce que ce sont tous deux des clients du serveur.
# Cependant, les actions qu'ils peuvent exécutés étant différentes, il a fallu distinguer ces 
# objets. Notamment dans le traitement d'un dossier de candidature, l'administrateur peut compléter certaines infos 
# (notes notamment) manquantes mais ne juge pas le dossier alors qu'un jury corrige le score brut, commente son choix, 
# mais ne touche pas au contenu du dossier.

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
        """ Retourne l'attribut _droits """
        return self._droits

    def get_cand(self) :
        """ renvoie le candidat courant """
        return self.fichier.cand(self.num_doss)
        
    def set_fichier(self, fich):
        """ Renseigne l'attribut 'fichier', et mets à jour les droits pour qu'ils contiennent la filière courante """
        # fich est une instance Fichier.
        self.fichier = fich
        r = parse('{}_{}.xml', fich.nom) # récupère nom de la filière traitée et éventuellement un numéro de jury.
        self._droits += ' {}'.format(r[1]) # ajoutée aux droits (apparaît dans l'entête de page html)
        self.num_doss = 0 # on commence par le premier dossier !

#################################################################################
#                               Class Jury                                      #
#################################################################################

class Jury(Client): 
    """  Objet client (de type jury de commission) pour la class Serveur """
    def __init__(self, key):
        """ constructeur : on créé une instance Client avec droits 'Jury'. """
        Client.__init__(self, key, 'Jury')
        # Fichiers javascripts. Ces attributs servent au Composeur de page html..
        self.script_menu = 'utils/scripts/menu_jury.js'
        self.script_dossiers = 'utils/scripts/dossiers_jury.js'

    def set_droits(self, droits):
        """ Renseigne l'attribut 'droits' de l'instance. """
        self._droits = 'Jury' + droits

    def get_rgfinal(self, cand):
        """ Renvoie une estimation du rg final d'un candidat """
        # On extrait du fichier les dossiers traités et non NC
        doss = [ca for ca in self.fichier if (Fichier.get(ca, 'traité') == 'oui' and Fichier.get(ca, 'Correction') != 'NC')]
        # On classes ceux-ci par ordre de score final décroissant
        doss[:] = sorted(doss, key = lambda cand: -float(Fichier.get(cand, 'Score final').replace(',','.')))
        # On calcule le rang du score_final actuel (celui de cand) dans cette liste
        rg = Fichier.rang(cand, doss, 'Score final')
        # À ce stade, rg est le rang dans la liste du jury. 
        # La suite consiste à calculer n*(rg-1) + k
        # où n est le nombre de jurys pour cette filière et k l'indice du jury courant.
        q = parse('Jury {:w}{:d}', self._droits) # n et k sont cachés dans les droits du jury !
        n = int(nb_jurys[q[0].lower()])
        k = int(q[1])
        return n*(rg-1)+k

    def traiter(self, **kwargs):
        """ Traiter un dossier """
        # Fonction lancée par la fonction "traiter" du Serveur, elle même lancée par un clic sur 'Classé' ou 'NC'
        cand  = self.get_cand() # on récupère le candidat
        ## On met à jour le contenu de ce dossier :
        # 1/ correction apportée par le jury et score final
        if kwargs['nc'] == 'NC': # cas d'un clic sur 'NC'
            cor, scoref = 'NC', '0'
        else: # cas d'un clic sur 'Classé'
            cor = kwargs['correc'] # récupération de la correction et calcul du score final
            note = float(Fichier.get(cand, 'Score brut').replace(',','.')) + float(cor)
            scoref = '{:.2f}'.format(note).replace('.',',')
        Fichier.set(cand, 'Correction', cor) # écriture de la correction dans le noeud xml du candidat
        Fichier.set(cand, 'Score final', scoref) # écriture du score final dans le noeud xml du candidat
        # 2/ Qui a traité le dossier : écriture du noeud xml adéquat
        Fichier.set(cand, 'Jury', self._droits)
        # 2bis/ mise à jour du fichier décomptes : ce fichier a été créé par admin, dans la méthode generation_comm
        if (not(Fichier.get(cand, 'traité')) and cor != 'NC'): # seulement si le candidat n'a pas déjà été vu et si classé!
            with open(os.path.join(os.curdir,"data","decomptes"), 'br') as fich:
                decompt = pickle.load(fich)
            qui = self._droits
            for key in decompt.keys():
                if key in qui:
                    decompt[key] += 1
            with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') as stat_fich:
                pickle.dump(decompt, stat_fich)
        # 3/ noeud 'traité' : le dossier a été traité (classé ou non)
        Fichier.set(cand, 'traité', 'oui')
        # 4/ motivation du jury
        Fichier.set(cand, 'Motifs', kwargs['motif'])
        ## Fin mise à jour dossier
        # On sélectionne le dossier suivant
        if self.num_doss < len(self.fichier)-1:
            self.num_doss += 1
        # Et on sauvegarde le tout
        self.fichier.sauvegarde() # sauvegarde physique du fichier.

#################################################################################
#                               Class Admin                                     #
#################################################################################
class Admin(Client): 
    """ Objet client (de type Administrateur) pour la class Serveur """
    def __init__(self, key): 
        """ constructeur : on créé une instance Client avec droits 'admin' """
        Client.__init__(self, key, 'Administrateur')
        # Fichiers javascripts. Ces attributs servent au Composeur de page html..
        self.script_menu = 'utils/scripts/menu_admin.js'
        self.script_dossiers = 'utils/scripts/dossiers_admin.js'
    
    def set_droits(self, droits):
        """ Renseigne l'attribut 'droits' de l'instance """
        self._droits = 'Administrateur' + droits

    def traiter(self, **kwargs):
        """ Traiter un dossier """
        # Fonction lancée par la fonction "traiter" du Serveur, elle même lancée par un clic sur 'Classé' ou 'NC'
        # On récupère le candidat courant
        cand = self.get_cand()
        # Ici, on va répercuter les complétions de l'administrateur dans tous les dossiers que le candidat a déposé.
        # Attention ! le traitement du fichier en cours est fait à part car deux objets 'Fichier' qui
        # auraient le même nom sont malgré tout différents !! On rajoute la bonne instance Fichier juste après.
        # Recherche de tous les fichiers existants :
        list_fich_admin = [Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))\
                if fich != self.fichier.nom]
        # On restreint la liste aux fichiers contenant le candidat en cours
        list_fich_cand = [fich for fich in list_fich_admin if cand in fich]
        # On rajoute le fichier suivi actuellement
        list_fich_cand.append(self.fichier)
        # list_fich_cand contient tous les fichiers dans lesquels le candidat courant se trouve.
        #
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
                    key_script = '{}{}{}'.format(cl[0], mat[0], da[-1]) # changera peut-être, les noms de notes dans
                    # le fichier patrons.html est 'stylisé' : PM1 pour Mathématiques Première trimestre 1.. 
                    key = '{} {} {}'.format(mat, cl, da)
                    if Fichier.get(cand, key) != kwargs[key_script]: # la note a-t-elle été modifiée ?
                        for fich in list_fich_cand: Fichier.set(fich.get_cand(cand), key, kwargs[key_script])
        # CPES et EAF
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
        # Les commentaires admin sont précédés de '- Admin :' c'est à cela qu'on les reconnaît. Et le jury les
        # verra sur fond rouge dans la liste de ses dossiers.
        # Par ailleurs, dossiers_jury.js exclut qu'un tel commentaire soit considéré comme une motivation de jury.
        motif = kwargs['motif']
        if not('- Admin :' in motif or motif == ''):
            motif = '- Admin : {}'.format(motif)
        if kwargs['nc'] == 'NC':
            # L'admin a validé le formulaire avec le bouton NC (le candidat ne passera pas en commission)
            # Pour ce cas là, on ne recopie pas dans toutes les filières. Admin peut exclure une candidature
            # dans une filière sans l'exclure des autres. Sécurité !
            Fichier.set(cand, 'Correction', 'NC') # la fonction calcul_scoreb renverra 0 !
            Fichier.set(cand, 'Jury', 'Admin') # Cette exclusion est un choix de l'admin (apparaît dans les tableaux)
            Fichier.set(cand, 'Motifs', motif)
        else:
            for fich in list_fich_cand:
                Fichier.set(fich.get_cand(cand), 'Motifs', motif)

        # On sauvegarde tous les fichiers retouchés
        for fich in list_fich_cand:
            fich.sauvegarde()

    def traiter_csv(self):
        """ Traiter les fichiers .csv en provenance de ParcoursSup. """
        # Cette méthode est un générateur. Ceci permet l'envoi au navigateur d'un indicateur d'avancement.
        yield "     Début du traitement des fichiers csv\n"
        for source in glob.glob(os.path.join(os.curdir, "data", "*.csv")): # On itère sur la liste des fichiers .csv
            for fil in filieres: # et sur chacune des filières
                if fil in source.lower(): # Attention pour être traité, le nom du fichier csv doit contenir la filière...
                    dest = os.path.join(os.curdir, "data", "admin_{}.xml".format(fil.upper())) # nom du fichier produit
                    yield "         Fichier {} ... ".format(fil.upper())
                    contenu_xml = lire(source) # première lecture brute
                    contenu_xml = nettoie(contenu_xml) # nettoyage doux, filtrage des dossiers invalides + Alertes
                    with open(dest, 'wb') as fich: # Écriture du fichier admin_FILIÈRE.xml
                        fich.write(etree.tostring(contenu_xml, pretty_print=True, encoding='utf-8'))
                    yield "traité.\n"

    def traiter_pdf(self):
        """ Traiter les fichiers .pdf en provenance de ParcoursSup. """
        # Générateur pour les mêmes raisons que traiter_csv..
        yield "\n     Début du traitement des fichiers pdf (traitement long, restez patient...)\n"
        dest = os.path.join(os.curdir, "data", "docs_candidats") # dossier destination
        restaure_virginite(dest) # un coup de jeune pour dest..
        for fich in glob.glob(os.path.join(os.curdir, "data", "*.pdf")): # itération sur tous les pdf trouvés
            for fil in filieres: # et sur toutes les filières
                if fil in fich.lower(): # un fichier n'est traité que si son nom contient une filière connue.
                    yield "         Fichier {} ... ".format(fil.upper())
                    desti = os.path.join(dest, fil)
                    os.mkdir(desti) # un dossier par filière
                    decoup(fich, desti) # fonction de découpage du pdf : dans la toolbox
                    yield "traité.\n".format(parse("{}_{4s}.pdf", fich)[1])

    def stat(self, list_fich):
        """ Effectue des statistiques sur les candidats """
        # On ordonne la liste de fichiers transmise selon l'ordre spécifié dans filieres (parametres.py)
        list_fich = sorted(list_fich, key = lambda f: filieres.index(f.filiere().lower()))
        # L'info de candidatures est stockée dans un mot binaire où 1 bit 
        # correspond à 1 filière. Un dictionnaire 'candid' admet ces mots binaires pour clés,
        # et les valeurs sont des nombres de candidats. 
        # candid = {'001' : 609, '011' : 245, ...} indique que 609 candidats ont demandé
        # la filière 1 et 245 ont demandé à la fois la filière 1 et la filière 2

        # Initialisation du dictionnaire stockant toutes les candidatures
        candid = {i : 0 for i in range(2**len(filieres))}

        # Recherche des candidatures # je suis très fier de cet algorithme !!
        # Construction des éléments de recherche
        l_dict = [ {Fichier.get(cand, 'Num ParcoursSup') : cand for cand in fich} for fich in list_fich ] # liste de dicos
        l_set = [ set(d.keys()) for d in l_dict ] # list d'ensembles (set()) d'identifiants ParcoursSup
        # Création des statistiques
        for (k,n) in enumerate(l_set): # k = index filière ; n = ensemble des identifiants des candidats dans la filière
            while len(n) > 0: # tant qu'il reste des identifiants dans n
                a = n.pop() # on en prélève 1 (et il disparait de n)
                cc, liste = 2**k, [k] # filière k : bit de poids 2**k au niveau haut.
                for i in range(k+1, len(list_fich)): # on cherche cet identifiant dans les autres filières.
                    if a in l_set[i]: # s'il y est :
                        cc |= 2**i # on met le bit 2**i au niveau haut (un ou exclusif est parfait) 
                        l_set[i].remove(a) # on supprime cet identifiant de l'ensemble des identifiants de la filière i
                        liste.append(i) # on ajoute la filière i à la liste des filières demandées par le candidat
                [Fichier.set(l_dict[j][a], 'Candidatures', cc) for j in liste] # On écrit le noeud 'Candidatures'
                for j in liste: # le test ci-dessous pourrait exclure les filières inadéquates (bien ou pas ?)..
                    if not('non validée' in Fichier.get(l_dict[j][a], 'Motifs')):
                        candid[2**j]+= 1 # ne sont comptés que les candidatures validées
                if len(liste) > 1: # si candidat dans plus d'une filière
                    candid[cc] += 1 # incrémentation du compteur correspondant
        # Sauvegarder
        [fich.sauvegarde() for fich in list_fich]
        
        # Écrire le fichier stat
        with open(os.path.join(os.curdir, "data", "stat"), 'wb') as stat_fich:
            pickle.dump(candid, stat_fich)

    def generation_comm(self):
        """ Création des fichiers commission """
        # Objectif : classer les candidats (fichier admin) par ordre de score brut décroissant et générer autant de 
        # fichiers qu'il y a de jurys dans la filière concernées. Ces fichiers sont construits de façon à ce qu'ils 
        # contiennent des candidatures également solides.
        # Récupération des fichiers admin
        list_fich = [Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))]
        # Pour chaque fichier "admin_*.xml"
        for fich in list_fich:
            # Tout d'abord, calculer (et renseigner le noeud) le score brut de chaque candidat 
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
                # Sauvegarde dans un fichier comm_XXXX.xml
                res = etree.Element('candidats')
                [res.append(cand) for cand in dossier]
                nom = os.path.join(os.curdir, "data", "comm_{}{}.xml".format(fich.filiere().upper(), j+1))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
        # Création fichier decompte : celui-ci contiendra en fin de commission le nombre de candidats traités pour 
        # chacune des filières. Ici, il est créé et initialisé. Il contient un dictionnaire {'filière' : nb, ...}
        decompt = {}
        for fil in filieres:
            decompt['{}'.format(fil.upper())] = 0
        with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') as stat_fich:
            pickle.dump(decompt, stat_fich)

    def clore_commission(self):
        """ Cloture la commission """
        # Objectif : récolter les fichiers comm en fin de commission, calculer tous les scores finals, classés les 
        # candidats et reconstituer un fichier unique par filière (class_XXX.xml). Enfin, construire des tableaux *.csv 
        # nécessaires à la suite du traitement administratif du recrutement (ces tableaux sont définis dans config.py)
        for fil in filieres: # pour chaque filière
            path = os.path.join(os.curdir, "data", "comm_{}*.xml".format(fil.upper()))
            list_fich = [Fichier(fich) for fich in glob.glob(path)] # récupération des fichiers comm de la filière
            list_doss = [] # contiendra les dossiers de chaque sous-comm
            # Pour chaque sous-commission
            for fich in list_fich:
                # Les fichiers non vus se voient devenir NC, score final = 0, avec
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
            doss_fin = [] # contiendra les dossiers intercalés comme il se doit..
            if list_doss: # Y a-t-il des dossiers dans cette liste ?
                nb = len(list_doss[0]) # (taille du fichier du 1er jury de cette filière)
                num = 0
                for i in range(0, nb): # list_doss[0] est le plus grand !!
                    doss_fin.append(list_doss[0][i])
                    for k in range(1, len(list_doss)): # reste-t-il des candidats classés dans les listes suivantes ?
                        if i < len(list_doss[k]): doss_fin.append(list_doss[k][i])
                res = etree.Element('candidats') # Création d'une arborescence xml 'candidats'
                [res.append(c) for c in doss_fin] # qu'on remplit avec les candidats classés.
                # Calcul et renseignement du rang final (index dans res)
                rg = 1
                for cand in res:
                    nu = 'NC'
                    if Fichier.get(cand, 'Correction') != 'NC': # si le candidat est classé
                        nu = str(rg)
                        rg += 1
                    Fichier.set(cand, 'Rang final', nu) # rang final = NC si non classé
                # Sauvegarde du fichier class...
                nom = os.path.join(os.curdir, "data", "class_{}.xml".format(fil.upper()))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, encoding='utf-8'))
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
                    # On ne met dans ces tableaux que les candidats traités, classés et dont le rang est inférieur à la 
                    # limite prévue dans config.py.
                    a = (Fichier.get(cand, 'traité') == 'oui')
                    b = (Fichier.get(cand, 'Correction') != 'NC')
                    c = not(b) or (int(Fichier.get(cand, 'Rang final')) <= int(nb_classes[fich.filiere().lower()]))
                    if a and b and c:
                        data = [Fichier.get(cand, champ) for champ in entetes]
                        cw.writerow(data)
            # Tableaux tous candidats : ces tableaux-là contiennent tous les candidats.
            for name in tableaux_tous_candidats:
                # Création du fichier csv
                nom = os.path.join(os.curdir, "tableaux", "{}_{}.csv".format(fich.filiere(), name))
                cw = csv.writer(open(nom, 'w'))
                entetes = tableaux_tous_candidats[name]
                cw.writerow(entetes)
                for cand in fich.ordonne('alpha'):
                    data = [Fichier.get(cand, champ) for champ in entetes]
                    cw.writerow(data)
