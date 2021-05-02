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

import os, glob, pickle, copy, csv, logging
from lxml import etree
from parse import parse
from utils.fichier import Fichier
from utils.csv_parcourssup import lire, ecrire
from utils.nettoie_xml import nettoie
from config import filieres, nb_jurys, nb_classes, tableaux_candidats_classes, tableaux_tous_candidats
from utils.toolbox import decoup, restaure_virginite, str_to_num, normalize_mark
from utils.parametres import min_correc

#################################################################################
#                               Class Client                                    #
#################################################################################

class Client(): 
    """ Objet client "abstrait" pour la class Serveur """
    def __init__(self, key, type_client):
        """ constructeur """
        # identifiant du client : contenu du cookie déposé sur la machine client
        self.je_suis = key  
        self.type = type_client # type de client (admin ou jury)
        self.journal = logging.getLogger('commission')#journal_de_log
        self._droits = type_client  # droits : (type suivi nom fichier).
        self.fichier = None  # contiendra une instance 'Fichier'
        # Index (dans le fichier) du candidat suivi.
        self.num_doss = -1  # -1 signifie : le jury n'est pas au travail
    
    def reset_droits(self):
        """ Restitue des droits vierges au client """
        self._droits = self.type

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
        r = parse('{}_{}.xml', fich.nom)
        self._droits = '{} {}'.format(self.type, r[1])
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

    def get_rgfinal(self, cand):
        """ Renvoie une estimation du rg final d'un candidat """
        # On extrait du fichier la liste des scores des dossiers traités et non NC
        doss = [ca.get('Score final') for ca in self.fichier\
                if (ca.get('traité') == 'oui' and ca.get('Correction') != 'NC')]
        # On classes ceux-ci par ordre de score final décroissant
        doss.sort(reverse = True)
        # On calcule le rang du score_final de cand dans cette liste
        try:
            rg = 1 + doss.index(cand.get('Score final'))
        except:
            return '-'
        # À ce stade, rg est le rang dans la liste du jury. 
        # La suite consiste à calculer n*(rg-1) + k où n est le nombre de jurys 
        # pour cette filière et k l'indice du jury courant.
        # n et k sont cachés dans les droits du jury !
        q = parse('Jury {:w}{:d}', self._droits)
        n = int(nb_jurys[q[0].lower()])
        k = int(q[1])
        return n*(rg-1)+k

    def traiter(self, **kwargs):
        """ Traiter un dossier """
        # Fonction lancée par la fonction "traiter" du Serveur, elle même lancée 
        # par un clic sur 'Classé' ou 'NC'
        cand  = self.get_cand() # on récupère le candidat
        # On récupère la correction apportée par le jury
        cor = float(kwargs['correc'])

        # précédente correction si le jury revient sur un candidat :
        cor_prec = cand.get('Correction')

        # Mise à jour du fichier décomptes 
        # ce fichier a été créé par admin, dans la méthode generation_comm
        a = (cand.get('traité') == 'oui')
        b = (cor_prec == 'NC')
        c = (cor == float(min_correc))
        if (not(a ^ b ^ c) and not(b and c)):
            # doit-on changer le nb de candidats classés?
            change_decompte = 1
            if c:
                # -1 si candidat classé qui devient non classé
                change_decompte = -1
            with open(os.path.join(os.curdir,"data","decomptes"), 'br') as fich:
                decompt = pickle.load(fich)
            qui = self._droits
            for key in decompt.keys():
                if key in qui:
                    decompt[key] += change_decompte
            with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') \
                    as stat_fich:
                pickle.dump(decompt, stat_fich)

        # On met à jour le contenu de ce dossier :
        # tout d'abord, calcul du score final
        if cor == float(min_correc): # cas d'un choix 'NC'
            cor, scoref = 'NC', 0
        else:
            scoref = cand.get('Score brut') + cor

        # Écriture des différents champs
        # 1/ correction et score final
        cand.set('Correction', cor)
        cand.set('Score final', scoref)

        # 2/ Qui a traité le dossier : écriture du noeud xml adéquat
        cand.set('Jury', self._droits)

        # 3/ noeud 'traité' : le dossier a été traité (classé ou non)
        cand.set('traité', 'oui')

        # 4/ motivation du jury
        cand.set('Motifs', kwargs['motif'])

        # Renseignement du journal de log
        self.journal.info(f"{self._droits} a traité {cand.get('Nom')} {cand.get('Prénom')} : {cor} / {kwargs['motif']}")

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
    
    def traiter(self, **kwargs):
        """ Traiter un dossier """
        # Fonction lancée par la fonction "traiter" du Serveur, elle même lancée 
        # par un clic sur 'Classé' ou 'NC'

        # On récupère le candidat courant
        cand = self.get_cand()

        # Ici, on va répercuter les complétions de l'administrateur dans tous 
        # les dossiers que le candidat a déposé.  Attention ! le traitement du 
        # fichier en cours est fait à part car deux objets 'Fichier' qui 
        # auraient le même nom sont malgré tout différents !! On rajoute la 
        # bonne instance Fichier juste après.

        # Recherche de tous les fichiers existants (sauf fichier en cours) :
        list_fich_admin = [Fichier(fich) \
                for fich in glob.glob(os.path.join(os.curdir, "data", \
                "admin_*.xml")) if fich != self.fichier.nom]

        # On restreint la liste aux fichiers contenant le candidat en cours
        list_fich_cand = [fich for fich in list_fich_admin if cand in fich]

        # On rajoute le fichier suivi actuellement
        list_fich_cand.append(self.fichier)

        # list_fich_cand contient tous les fichiers dans lesquels le candidat 
        # courant se trouve.
        #
        ############### Admin a-t-il changé qqc ? Si oui, mise à jour. 
        # Classe actuelle ?
        if cand.get('Classe actuelle') != kwargs['Classe actuelle']:
            for fich in list_fich_cand:
                fich.get_cand(cand).set('Classe actuelle', \
                        kwargs['Classe actuelle'])

        # Cas des notes de première
        matiere = ['Mathématiques Spécialité', 'Physique-Chimie Spécialité']
        date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
        for mat in matiere:
            for da in date:
                key = '{} Première {}'.format(mat, da)
                if cand.get(key) != str_to_num(normalize_mark(kwargs[key])):
                    # si note modifiée 
                    self.journal.debug(f"{cand.get('Nom')} {cand.get('Prénom')} : admin a saisi '{kwargs[key]}' comme note de {key}")
                    for fich in list_fich_cand:
                        fich.get_cand(cand).set(key, kwargs[key])

        # Cas des notes de terminale
        matiere = ['Mathématiques Spécialité', 'Mathématiques Expertes', \
                'Physique-Chimie Spécialité']
        date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
        for mat in matiere:
            for da in date:
                key = '{} Terminale {}'.format(mat, da)
                if cand.get(key) != str_to_num(normalize_mark(kwargs[key])):
                    # si note modifiée
                    self.journal.debug(f"{cand.get('Nom')} {cand.get('Prénom')} : admin a saisi '{kwargs[key]}' comme note de {key}")
                    for fich in list_fich_cand:
                        fich.get_cand(cand).set(key, kwargs[key])

        # CPES et EAF
        # liste = ['Mathématiques CPES', 'Physique/Chimie CPES', 'Écrit EAF', 
        # 'Oral EAF']
        # Seulement EAF depuis 2020
        liste = ['Écrit EAF', 'Oral EAF']
        for li in liste:
            formated_mark = str_to_num(normalize_mark(kwargs[li]))
            if 'cpes' in li.lower():
                if (cand.is_cpes() and cand.get(li) != formated_mark):
                    for fich in list_fich_cand:
                        fich.get_cand(cand).set(li, kwargs[li])
            else:
                if cand.get(li) != formated_mark:
                    for fich in list_fich_cand:
                        fich.get_cand(cand).set(li, kwargs[li])

        # Commentaire éventuel admin + gestion des 'NC'
        # Les commentaires admin sont précédés de '- Admin :' c'est à cela qu'on 
        # les reconnaît. Et le jury les verra sur fond rouge dans la liste de 
        # ses dossiers.  Par ailleurs, dossiers_jury.js exclut qu'un tel 
        # commentaire soit considéré comme une motivation de jury.
        motif = kwargs['motif']
        if not('- Admin :' in motif or motif == '' or '- Alerte :' in motif):
            motif = '- Admin : {}'.format(motif)

        # Récupération de la correction. On en fait qqc seulement si elle est 
        # minimale (NC), puis calcul du score final
        cor = kwargs['correc']
        if float(cor) == float(min_correc):
            # L'admin a validé le formulaire avec la correction NC (le candidat 
            # ne passera pas en commission) Pour ce cas là, on ne recopie pas 
            # dans toutes les filières. Admin peut exclure une candidature dans 
            # une filière sans l'exclure des autres. Sécurité !
            cand.set('Correction', 'NC') # update_raw_score renverra 0 !
            cand.set('Jury', 'Admin') # exclu par l'admin
            cand.set('Motifs', motif)
        else:
            cand.set('Correction', '0')
            # 2 lignes nécessaires si l'admin a NC un candidat, puis a changé 
            # d'avis.
            cand.set('Jury', '')
            for fich in list_fich_cand:
                fich.get_cand(cand).set('Motifs', motif)

        # On (re)calcule le score brut !
        cand.update_raw_score()
        # On sauvegarde tous les fichiers retouchés
        for fich in list_fich_cand:
            fich.sauvegarde()

    def traiter_csv(self):
        """ Traiter les fichiers .csv en provenance de ParcoursSup. """
        # Cette méthode est un générateur. Ceci permet l'envoi au navigateur 
        # d'un indicateur d'avancement.

        # On itère sur la liste des fichiers .csv
        for source in glob.glob(os.path.join(os.curdir, "data", "*.csv")):
            # et sur chaque filière
            for fil in filieres:
                # Attention pour être traité, le nom du fichier csv doit 
                # contenir la filière...
                if fil in source.lower():
                    dest = os.path.join(os.curdir, "data", "admin_{}.xml"\
                            .format(fil.upper())) # nom du fichier produit
                    yield "Fichier {} ... ".format(fil.upper())
                    # première lecture brute
                    contenu_xml = lire(source)
                    # nettoyage doux, filtrage des dossiers invalides + Alertes
                    contenu_xml = nettoie(contenu_xml)
                    # Écriture du fichier admin_FILIÈRE.xml
                    ecrire(dest, contenu_xml)
                    yield "traité."

    def traiter_pdf(self):
        """ Traiter les fichiers .pdf en provenance de ParcoursSup. """
        # Générateur pour les mêmes raisons que traiter_csv..
        
        # # dossier destination
        dest = os.path.join(os.curdir, "data", "docs_candidats")
        restaure_virginite(dest) # un coup de jeune pour dest..

        #  # itération sur tous les pdf trouvés
        for fich in glob.glob(os.path.join(os.curdir, "data", "*.pdf")):
            for fil in filieres: # et sur toutes les filières
                #  un fichier n'est traité que si son nom contient une filière 
                #  connue.
                if fil in fich.lower():
                    yield "Fichier {} ... ".format(fil.upper())
                    desti = os.path.join(dest, fil)
                    os.mkdir(desti) # un dossier par filière
                    decoup(fich, desti) # fonction de découpage du pdf
                    yield "traité.".format(parse("{}_{4s}.pdf", fich)[1])

    def appel_stat(self):
        """ Appelée par le serveur après que l'Admin ait appuyé sur le bouton 
        'Traiter / Valider. Lancer la fonction stat ci-dessous, en renvoyant un 
        état de la progression, pour le rafraichissement de la page html. """
        yield 'Décompte ... '
        self.stat()
        yield 'effectué.'

    def stat(self):
        """ Effectue des statistiques sur les candidats """
        # Récupère la liste des fichiers concernés
        list_fichiers = [Fichier(fich) \
                for fich in glob.glob(os.path.join(os.curdir, "data", \
                "admin_*.xml"))]

        # On ordonne la liste de fichiers transmise selon l'ordre spécifié dans 
        # filieres (parametres.py)
        list_fich = sorted(list_fichiers, \
                key = lambda f: filieres.index(f.filiere().lower()))

        # L'info de candidatures est stockée dans un mot binaire où 1 bit 
        # correspond à 1 filière. Un dictionnaire 'candid' admet ces mots 
        # binaires pour clés, et les valeurs sont des nombres de candidats.  
        # candid = {'001' : 609, '011' : 245, ...} indique que 609 candidats ont 
        # demandé la filière 1 et 245 ont demandé à la fois la filière 1 et la 
        # filière 2

        # Initialisation du dictionnaire stockant toutes les candidatures
        candid = {i : 0 for i in range(2**len(filieres))}

        # Variables de décompte des candidats (et pas candidatures !)
        candidats = 0
        candidats_ayant_valide = 0

        # Recherche des candidatures # je suis très fier de cet algorithme !!
        # Construction des éléments de recherche

        # # liste de dicos 
        l_dict = [ {cand.get('Num ParcoursSup') : cand for cand in fich} \
                for fich in list_fich ]
        # # liste d'ensembles d'identifiants ParcoursSup
        l_set = [ set(d.keys()) for d in l_dict ]

        # Création des statistiques
        for (k,n) in enumerate(l_set):
            # k = index filière ; n = ensemble des identifiants des candidats 
            # dans la filière
            while len(n) > 0: # tant qu'il reste des identifiants dans n
                a = n.pop() # on en prélève 1 (et il disparait de n)
                candidats += 1
                cc, liste = 2**k, [k] # filière k : bit de poids 2**k à 1
                for i in range(k+1, len(list_fich)):
                    # on cherche cet identifiant dans les autres filières.
                    if a in l_set[i]: # s'il y est :
                        cc |= 2**i # on met le bit 2**i à 1 (un xor est parfait) 
                        #  on supprime cet identifiant de l'ensemble des 
                        #  identifiants de la filière i
                        l_set[i].remove(a)
                        #  on ajoute la filière i à la liste des filières 
                        #  demandées par le candidat
                        liste.append(i)

                #  # On écrit le noeud 'Candidatures'
                [l_dict[j][a].set('Candidatures', cc) for j in liste]
                flag = True # pour ne compter qu'une validation par candidat !
                for j in liste:
                    # le test ci-dessous pourrait exclure les filières 
                    # inadéquates (bien ou pas ?)..
                    if not('non validée' in l_dict[j][a].get('Motifs')):
                        # ne sont comptés que les candidatures validées
                        candid[2**j]+= 1
                        if flag:
                            candidats_ayant_valide += 1
                            flag = False
                if len(liste) > 1: # si candidat dans plus d'une filière
                    candid[cc] += 1 # incrémentation du compteur correspondant
        # Sauvegarder
        [fich.sauvegarde() for fich in list_fich]
        # Ajouter deux éléments dans le dictionnaire candid
        candid['nb_cand'] = candidats
        candid['nb_cand_valid'] = candidats_ayant_valide
        # Écrire le fichier stat
        with open(os.path.join(os.curdir, "data", "stat"), 'wb') as stat_fich:
            pickle.dump(candid, stat_fich)
        return

    def generation_comm(self):
        """ Création des fichiers commission """
        # Objectif : classer les candidats (fichier admin) par ordre de score 
        # brut décroissant et générer autant de fichiers qu'il y a de jurys dans 
        # la filière concernée. Ces fichiers sont construits de façon à ce 
        # qu'ils contiennent des candidatures également solides.
        # Récupération des fichiers admin
        list_fich = [Fichier(fich) \
                for fich in glob.glob(os.path.join(os.curdir, "data", \
                "admin_*.xml"))]
        # Pour chaque fichier "admin_*.xml"
        for fich in list_fich:
            # Tout d'abord, calculer (et renseigner le noeud) le score brut de 
            # chaque candidat 
            for cand in fich:
                cand.update_raw_score()
            # Classement par scoreb décroissant
            doss = fich.ordonne(Fichier.Critere.SCORE_BRUT)
            # Calcul du rang de chaque candidat et renseignement du noeuds 
            # 'rang_brut'
            for cand in fich:
                cand.set('Rang brut',  1 + doss.index(cand))
            # Récupération de la filière et du nombre de jurys 
            nbjury = int(nb_jurys[fich.filiere().lower()])
            # Découpage en n listes de dossiers
            for j in range(nbjury):
                dossier = []
                # deepcopy ligne suivante sinon les candidats sont retirés de 
                # doss à chaque append
                [dossier.append(copy.deepcopy(doss[i])) \
                        for i in range(len(doss)) if i%nbjury == j]
                # Sauvegarde dans un fichier comm_XXXX.xml
                res = etree.Element('candidats')
                [res.append(cand.get_node()) for cand in dossier]
                nom = os.path.join(os.curdir, "data", "comm_{}{}.xml"\
                        .format(fich.filiere().upper(), j+1))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, \
                            encoding='utf-8'))
        # Création fichier decompte : celui-ci contiendra en fin de commission 
        # le nombre de candidats traités pour chacune des filières. Ici, il est 
        # créé et initialisé. Il contient un dictionnaire {'filière' : nb, ...}
        decompt = {}
        for fil in filieres:
            decompt['{}'.format(fil.upper())] = 0
        with open(os.path.join(os.curdir, "data", "decomptes"), 'wb') \
                as stat_fich:
            pickle.dump(decompt, stat_fich)

    def clore_commission(self):
        """ Cloture la commission """
        # Objectif : récolter les fichiers comm en fin de commission, calculer 
        # tous les scores finals, classés les candidats et reconstituer un 
        # fichier unique par filière (class_XXX.xml). Enfin, construire des 
        # tableaux *.csv nécessaires à la suite du traitement administratif du 
        # recrutement (ces tableaux sont définis dans config.py)
        for fil in filieres: # pour chaque filière
            path = os.path.join(os.curdir, "data", "comm_{}*.xml"\
                    .format(fil.upper()))
            # récupération des fichiers comm de la filière
            list_fich = [Fichier(fich) for fich in glob.glob(path)]

            # l'ordre est important pour la suite
            list_fich = sorted(list_fich, key = lambda fich: fich.nom)
            list_doss = [] # contiendra les dossiers de chaque sous-comm

            # Pour chaque sous-commission
            for fich in list_fich:
                # Les candidats non vus se voient devenir NC, score final = 0, 
                # avec motifs = "Dossier moins bon que le dernier classé" (sauf 
                # s'il y a déjà un motif - Admin)
                for c in fich:
                    if c.get('traité') != 'oui':
                        c.set('Correction', 'NC')
                        c.set('Score final', 0)
                        if c.get('Jury') == 'Auto': # pas de motif Admin
                            c.set('Motifs', \
                                    'Dossier moins bon que le dernier classé.')

                # list_doss récupère la liste des dossiers classée selon 
                # score_final + age
                list_doss.append(fich.ordonne(Fichier.Critere.SCORE_FINAL))

            # Ensuite, on entremêle les dossiers de chaque sous-comm
            doss_fin = [] # contiendra les dossiers intercalés comme il se doit..
            if list_doss: # Y a-t-il des dossiers dans cette liste ?
                # (taille du fichier du 1er jury de cette filière)
                nb = len(list_doss[0])
                num = 0
                for i in range(nb): # list_doss[0] est le plus grand !!
                    doss_fin.append(list_doss[0][i])
                    for k in range(1, len(list_doss)):
                        # reste-t-il des candidats classés dans les listes 
                        # suivantes ?
                        if i < len(list_doss[k]):
                            doss_fin.append(list_doss[k][i])

                # Calcul et renseignement du rang final (index dans doss_fin)
                rg = 1
                for cand in doss_fin:
                    nu = 'NC'
                    if cand.get('Correction') != 'NC': # si le candidat est classé
                        nu = rg
                        rg += 1
                    cand.set('Rang final', nu)

                # Création d'une arborescence xml 'candidats'
                res = etree.Element('candidats')
                # qu'on remplit avec les candidats classés.
                [res.append(c.get_node()) for c in doss_fin]

                # Sauvegarde du fichier class...
                nom = os.path.join(os.curdir, "data", "class_{}.xml"\
                        .format(fil.upper()))
                with open(nom, 'wb') as fichier:
                    fichier.write(etree.tostring(res, pretty_print=True, \
                            encoding='utf-8'))

        # On lance la génération des tableaux bilan de commission
        list_fich = [Fichier(fich) \
                for fich in glob.glob(os.path.join(os.curdir, "data", \
                "class_*.xml"))]
        self.tableaux_bilan(list_fich)

    def tableaux_bilan(self, list_fich):
        """ Cette fonction créé les tableaux dont a besoin l'admin pour la suite 
        du recrutement """
        # Un peu de ménage...
        dest = os.path.join(os.curdir, "tableaux")
        restaure_virginite(dest)

        # Pour chaque filière :
        for fich in list_fich:
            # Tableaux candidats classés
            for name in tableaux_candidats_classes.keys():
                # Création du fichier csv
                nom = os.path.join(os.curdir, "tableaux", "{}_{}.csv"\
                        .format(fich.filiere(), name))
                cw = csv.writer(open(nom, 'w'))
                entetes = tableaux_candidats_classes[name]
                cw.writerow(entetes)

                for cand in fich:
                    # On ne met dans ces tableaux que les candidats traités, 
                    # classés et dont le rang est inférieur à la limite prévue 
                    # dans config.py.

                    #  # récupération du contenu du fichier config.py
                    nb = nb_classes[fich.filiere().lower()]
                    # Si nb n'est pas convertible en un entier positif alors on 
                    # classe tous les candidats
                    try:
                        nb_max = int(nb)
                        if nb_max < 0: nb_max = len(fich)
                    except:
                        nb_max = len(fich)
                    a = (cand.get('traité') == 'oui')
                    b = (cand.get('Correction') != 'NC')
                    c = not(b) or (cand.get('Rang final') <= nb_max)
                    if a and b and c:
                        data = [cand.get(champ) for champ in entetes]
                        cw.writerow(data)

            # Tableaux tous candidats : ces tableaux-là contiennent tous les 
            # candidats.
            for name in tableaux_tous_candidats:
                # Création du fichier csv
                nom = os.path.join(os.curdir, "tableaux", "{}_{}.csv"\
                        .format(fich.filiere(), name))
                cw = csv.writer(open(nom, 'w'))
                entetes = tableaux_tous_candidats[name]
                cw.writerow(entetes)
                for cand in fich.ordonne(Fichier.Critere.NOM):
                    data = [cand.get(champ) for champ in entetes]
                    cw.writerow(data)
