#!/usr/bin/env python3
#-*- coding: utf-8 -*-

# Ce fichier contient la classe Composeur
#   Un objet Composeur tout ce qui sert à composer le code html; Il est
#   mandaté par le serveur à chaque fois qu'une page doit être envoyée à
#   un client.

import os, glob, pickle, logging
from parse import parse
from utils.parametres import min_correc, max_correc, nb_correc
from config import filieres, motivations, nb_classes
from utils.fichier import Fichier
from utils.clients import Jury, Admin
from utils.toolbox import division_to_xml, xml_to_division

#################################################################################
#                               Composeur                                       #
#################################################################################
class Composeur(object):
    """Composeur de pages html. Lui sont donnés, un objet client, un type de page
    (menu ou traitement), éventuellement un candidat ou toute autre information
    utile (statistiques, ..)"""

    ### Attributs de classe
    # Cet premier attribut nommé 'html' est un dictionnaire, contenant des patrons
    # de page ou de morceaux de page (entête, dossier, liste des dossiers, etc.).
    # Chacun de ces patrons (contenus dans le fichier 'patrons.html') se présente
    # sous la forme d'une chaîne de caractères prête à être 'formatée'.
    # Par exemple, la chaîne :
    # ch = "Demain je {action} la cuisine"
    # pourra être formatée par la syntaxe :
    # ch.format(**{'action' : 'fais'})
    # ou bien la syntaxe :
    # action = 'fais'
    # ch = f"Demain je {action} la cuisine"
    # C'est ainsi qu'on obtient des pages html "dynamiques"
    # (dont le contenu change en fonction du contexte).
    html = {}
    # Chargement des patrons :
    with open(os. path. join(os.curdir, "utils", "patrons.html"), "r",\
            encoding="utf8") as fi:
        for ligne in fi:
            if ligne.startswith("[*"):  # étiquette trouvée ==>
                label = ligne.strip()   # suppression LF et esp évent.
                label = label[2:-2]     # suppression [* et *]
                txt = ""                # début d'une page html
            else:
                if ligne.startswith("#####"):   # fin d'une page html
                    html[label] = txt           # on remplit le dictionnaire
                else:
                    txt += ligne

    # corrections proposées aux jurys
    # (faire attention que 0 soit dans la liste !!)
    # Cette liste sert à fabriquer la barre de correction proposée aux jurys.
    corrections = [(n+min_correc*nb_correc)/float(nb_correc)\
            for n in range(0, (max_correc-min_correc)*nb_correc+1)]

    # Barre de correction :
    # Elle s'inscrit dans une 'table' html à 3 colonnes
    # (score brut | barre | score final)
    barre = f"""<input type = "range" class = "range no_impr" min="{min_correc}"
            max = "{max_correc}" step = "{1/float(nb_correc)}" 
            name = "correc" id = "correc" onchange="javascript:maj_note();"
            onmousemove="javascript:maj_note();" onclick="click_range();"
            """
    barre += ' value = "{}"/>' # champ rempli dans la fonction 'genere_action'
    # on construit maintenant la liste des valeurs...
    barre += '<div class="row no_impr">'
    for index, valeur in enumerate(corrections):
        if index == 0: # on remplace la valeur min par NC.
            barre += '<div class="tick">NC</div>'
        elif (index % 2 == 0):
            barre += f'<div class="tick">{valeur:+3.1f}</div>'
    barre += "</div>"
    barre += '<span class = "impr">{} : {:+1.2f}</span>' # champs remplis
    # dans la fonction 'genere_action'

    # Liste des motivations
    # Le premier élément est une zone de texte
    motifs = """
            <input type="text" class = "txt_motifs" name="motif"
            id = "motif" value= "{}"/>"""
    # La suite, les motifs pré-définis dans config.py
    for index, motif in enumerate(motivations):
            # cette clé sert au code javascript de la page..
            key = f"mot_{str(index)}"
            motifs += f'<input type="button" name="{key}"'
            motifs += f' id="{key}" onclick="javascript:maj_motif(this.id)"'
            motifs += f' class = "motif no_impr" value ="{motif}"/>'
    ### Fin déclaration attributs de classe

    def __init__(self, titre):
        """ constructeur d'une instance Composeur.
        Reçoit une titre de page en paramètre. """
        self.titre = titre
        self.journal = logging.getLogger('commission')

    # Méthodes
    def format_mark(self, mark):
        """ Met en forme les notes et les scores pour affichage """
        if type(mark) == float:
            return f'{mark:.2f}'.replace('.', ',')
        else:
            return mark

    def genere_entete(self, titre):
        """ Génère le code html de l'entête de page """
        return Composeur.html['Entete'].format(**{'titre' : titre})

########################################################
##### Ici, le code de la page 'barre d'avancement' #####
########################################################

    def page_progression(self, action):
        """ Générateur qui renvoie une page indiquant la progression dans
        le traitement des méthodes (générateurs elles-aussi) présentes
        dans la liste 'action' """
        # 'action' est au format [ (méthode, 'message à afficher'), etc ]
        # Chaque méthode est un générateur qui renvoie des 'yield' par paires :
        # 'je commence ...' puis 'j ai fini'
        ### On débute par l'entête de page et un titre :
        page_content = {}
        page_content['title'] = 'Traitement des données ParcoursSup'
        page_content['main_content'] = ''
        page_content['script'] = ''
        page = Composeur.html['Page'].format(**page_content)
        # On récupère la balise <meta> car elle doit être envoyée avec chaque
        # yield sinon on n'a pas le fonctionnement en 'temps réel'
        meta_content = parse('{}<meta{}>{}', page)[1]
        meta = f'<meta{meta_content}>'
        # On récupère ce qui précède {main_content} et ce qui le suit
        init_page = parse('{}"main_container">{}', page)[0]
        init_page += '"main_container">'
        close_page = parse('{}<script{}', page)[1]
        close_page = '<script' + close_page
        # Peut-être pas très propre mais ça fonctionne...
        # Ici, on envoie le titre et ouvre une <div> qui contiendra la suite
        yield f'{init_page}<div>'
        # Début du traitement du contenu du dico
        for gen, title in action:
            yield f"{meta}<h2>{title}</h2>" # On envoie le sous-titre
            flag = True # drapeau servant dans le traitement de la paire de \
                    # yield citée ci-dessus..
            for txt in gen(): # sollicitation du générateur jusqu'à épuisement
                if flag: # 1e partie de la ligne : "<p>Fichier blabla ..."
                    txt = f'<p>{txt}'
                else: # 2e partie de la ligne : on affiche "traité</p>"
                    txt = f'{txt}</p>'
                yield f'{meta}{txt}'
                flag ^= 1 # on change flag en son complémentaire
        ## Fin du traitement ##
        # Bouton retour au menu
        bouton = """<div style="align:center;">\
                <form action="/affiche_menu" method = POST>
                <input type = "submit" class ="grand bouton taille2"\
                value = "CLIQUER POUR RETOURNER AU MENU"></form></div></div>"""
        yield f'{meta}{bouton}{close_page}'


########################################################
##### Ici commence ce qui concerne les pages menus #####
########################################################
    def make_sous_menu(self, sous_menu_id, title, data):
        content = Composeur.html[f'sous_menu_content_{sous_menu_id}']\
                .format(**data)
        return Composeur.html['sous_menu'].format(**{'title' : title, 
                    'sous_menu_content' : content})

    def buttons_wrapper(self, title, list_fich): 
        txt = f""" <h3>{title}</h3> <div class='wrapper'> """
        list_fich.sort()
        for fich in list_fich:
            txt += f"""<div>
            <input type="submit" class = "petit bouton taille1 fichier" \
                    name="fichier" value="{xml_to_division(fich)}"/>
                    </div>"""
        return txt + '</div>'

    def menu(self, qui = None, fichiers_utilises = None, comm_en_cours = False): 
        """ compose le menu du client 'qui'
        fichiers_utilises est un dictionnaire qui contient les fichiers déjà
        choisis par un jury. Permet d'éviter que deux jurys travaillent
        sur un même fichier.
        comm_en_cours est un booléen qui permet d'adapter le menu de
        l'administrateur lorsque la commission se déroule. """
        if isinstance(qui, Admin):
            return self.menu_admin(qui, fichiers_utilises, comm_en_cours)
        else:
            return self.menu_comm(qui, fichiers_utilises)

    def menu_comm(self, qui, fichiers_utilises):
        """ compose le menu du jury 'qui'
        Fichiers utilisés est une liste des fichiers déjà choisis par un jury
        Ces fichiers sont inaccessibles (bouton disabled) """
        page_content = {}
        page_content['title'] = f'{self.titre} - Accès {qui.get_droits()}.'
        ## Contenu = liste de fichiers
        # Recherche des fichiers destinés à la commission
        list_fich = glob.glob(division_to_xml('jury', '*'))
        # Tout d'abord, on supprime de cette liste les fichiers qu'un jury a 
        # déjà choisi
        list_fich = [ fich for fich in list_fich \
                if not fich in fichiers_utilises.values() \
                    or fich == fichiers_utilises.get(qui, 'rien') ]

        txt = ''
        # Chaque fichier apparaîtra sous la forme d'un bouton
        if (len(list_fich) > 0):
            txt = self.buttons_wrapper(\
                    'Veuillez sélectionner la filière que vous souhaitez \
                        traiter.', list_fich)
        ## Fabrication de la page
        page_content['main_content'] = Composeur.html["menu_comm"]\
                .format(**{'liste' : txt, 'script' : qui.script_menu})
        page_content['script'] = qui.script_menu
        return Composeur.html["Page"].format(**page_content)

    def menu_admin(self, qui, fichiers_utilises, comm_en_cours):
        """ Compose le menu administrateur
        contenu : selon l'état (phase 1, 2 ou 3) du traitement
        phase 1 : avant la commission, l'admin gère ce qui provient de \
                ParcoursSup, commente et/ou complète les dossiers
        phase 2 : l'admin a généré les fichiers destinés à la \
                commission. Les différents jurys doivent se prononcer sur \
                les dossiers. C'est le coeur de l'opération de sélection.
        phase 3 : commission terminée. L'admin doit gérer "l'après sélection" :\
                recomposer un fichier ordonné par filière, générer tous les \
                tableaux récapitulatifs. """
        page_content = {}
        page_content['title'] = f'{self.titre} - Accès {qui.get_droits()}.'
        sous_menus = ""

        list_fich_comm = glob.glob(division_to_xml('jury' ,'*'))
        # On teste l'existence de fichiers destinés aux jurys.
        if len(list_fich_comm) > 0: # phase 2 ou 3
            data = {}
            data['decompt'] = self.genere_liste_decompte()
            data['liste_stat'] = self.genere_liste_stat(qui)

            # comm_en_cours est un booléen qui est True si des jurys sont 
            # connectés.
            if comm_en_cours: # phase 2
                title = 'Commission en cours...'
                txt = ''
                list_fich = [fich for fich in fichiers_utilises.values() ] 
                txt = self.buttons_wrapper('', list_fich)
                data['liste_jurys'] = txt
                sous_menus += self.make_sous_menu('comm', title, data)

            else: # phase 3
                # Des fichiers jurys existent, mais aucun jury connecté. On 
                # propose à l'admin un menu de fin de commission.
                ######## 4e sous-menu
                title = """- 4e étape : récolter le travail de la 
                commission..."""
                # Etape 4 bouton
                data['bout_etap4'] = """<input type = "button" 
                class ="petit bouton taille1 fichier" 
                value = "Récolter les fichiers" 
                onclick = "recolt_wait();"/>"""
                sous_menus += self.make_sous_menu('4', title, data)

                ######## 5e sous-menu
                # Etape 5 bouton et Etape 6
                title = """- 5e étape : Bilan de la commission :"""
                data = {}
                list_fich_class = \
                        glob.glob(division_to_xml('classement_final', '*'))
                data['liste_impression'] = ''
                if len(list_fich_class) > 0:
                    data['liste_impression'] = self.genere_liste_impression()
                sous_menus += self.make_sous_menu('5', title, data)

        else: # avant commission
            ######## 1er sous-menu
            title = """- 1e étape : digérer les données ParcoursSUP présentes 
            dans le dossier data :"""
            data = {}
            # liste csv
            data['liste_csv'] = self.genere_liste_csv()
            # liste pdf
            data['liste_pdf'] = self.genere_liste_pdf()
            sous_menus += self.make_sous_menu('1', title, data)

            ######## 2e sous-menu
            title = """- 2e étape : compléter les dossiers qui le 
            nécessitent..."""
            data = {}
            # liste admin
            data['liste_admin'] = self.genere_liste_admin()
            # liste_stat
            data['liste_stat'] = self.genere_liste_stat(qui)
            sous_menus += self.make_sous_menu('2', title, data)

            ######## 3e sous-menu
            title = """- 3e étape : générer les fichiers pour la 
            commission..."""
            # Etape 3 bouton : ce bouton n'est actif que si admin a levé 
            # toutes les alertes.
            ### Testons s'il reste encore des alertes dans les fichiers admin
            # Récupération des fichiers admin
            list_fich = {Fichier(fich) \
                    for fich in glob.glob(division_to_xml('admin', '*'))}
            alertes = False
            while not(alertes) and len(list_fich) > 0:
                # à la première alerte détectée alertes = True
                fich = list_fich.pop()
                alertes = ( True in {'- Alerte :' in cand.get('Motifs')\
                        for cand in fich if cand.get('Correction') != 'NC'} )
            ### Suite
            txt = ''
            if len(data['liste_admin']) > 0: # si les fichiers admin existent :
                txt = '<input type = "button" class ="petit bouton taille1" \
                        value = "Générer les fichiers commission"'
                affich = ''
                if (alertes):
                    affich = 'disabled'
                txt += f'onclick = "genere_wait();" {affich}/>'
            data = {}
            data['bout_etap3'] = txt
            sous_menus += self.make_sous_menu('3', title, data)
        # Envoyez le menu
        page_content['main_content'] = sous_menus
        page_content['script'] = qui.script_menu
        # Composition de la page
        return Composeur.html["Page"].format(**page_content)
    
    def genere_liste_csv(self):
        """ Sous-fonction pour le menu admin : liste des .csv trouvés """
        txt = ''
        for fich in glob.glob(os.path.join(os.curdir,"data","*.csv")):
            pattern = os.path.join(os.curdir, "data", "{}")
            txt += f'{parse(pattern, fich)[0]}<br>'
        return txt
    
    def genere_liste_pdf(self):
        """ Sous-fonction pour le menu admin : liste des .pdf trouvés """
        txt = ''
        for fich in glob.glob(os.path.join(os.curdir,"data","*.pdf")):
            pattern = os.path.join(os.curdir, "data", "{}")
            txt += f'{parse(pattern, fich)[0]}<br>'
        return txt
    
    def genere_liste_stat(self, qui):
        """ Sous-fonction pour le menu admin :
            affichage des statistiques de candidatures """
        liste_stat = ''
        if len(glob.glob(division_to_xml('admin', '*'))) > 0:
            # si les fichiers admin existent
            # lecture du fichier stat
            chem = os.path.join(os.curdir, "data", "stat")
            if not(os.path.exists(chem)):
                # le fichier stat n'existe pas (cela ne devrait pas arriver)
                # on le créé
                list_fich = [Fichier(fich) \
                        for fich in glob.glob(\
                        division_to_xml('admin', '*'))]
                qui.stat()
            # maintenant on peut effectivement lire le fichier stat
            with open(os.path.join(os.curdir, "data", "stat"), 'br') as fich:
                stat = pickle.load(fich)
            # Création de la liste à afficher
            liste_stat = f"<div class='taille-1 bold'>Statistiques \
                    (dossiers recevables) : {stat['nb_cand']} candidats.</div>"
            # Pour commencer les sommes par filières
            liste_stat += '<ul class="noMargin">'
            deja_fait = [0] # sert au test ci-dessous si on n'a pas math.log2()
            for i in range(len(filieres)):
                liste_stat += f'<li>{stat[2**i]} dossiers \
                        {filieres[i].upper()}</li>'
                deja_fait.append(2**i)
            # Ensuite les requêtes croisées
            liste_stat += 'dont :<ul class="taille-1">'
            for i in range(2**len(filieres)):
                if not(i in deja_fait):
                    # avec la fonction math.log2 ce test serait facile !!!
                    seq = []
                    # bina est la représentation binaire de i sur un nombre de 
                    # bits égal au nombre de filières
                    pattern = "{" + f"0:0{len(filieres)}b" + "}"
                    bina = pattern.format(i)
                    for char in range(len(bina)):
                        if bina[-char-1] == '1':
                            seq.append(filieres[char].upper())
                    txt = ' + '.join(seq)
                    if stat[i]:
                        liste_stat += f'<li>{stat[i]} dossiers {txt}</li>'
            liste_stat += '</ul></ul>'
        return liste_stat

    def genere_liste_admin(self):
        """ Sous-fonction pour le menu admin : liste des filières à traiter """
        list_fich = glob.glob(division_to_xml('admin', '*'))
        txt = ''
        if len(list_fich) > 0:
            txt = self.buttons_wrapper(\
                    'Choisissez la filière que vous souhaitez traiter',
                    list_fich)
        return txt
    
    def genere_liste_decompte(self):
        """ Sous-fonction pour le menu admin (pendant commission) :
            avancement de la commission """
        try: # normalement, decomptes existe !
            with open(os.path.join(os.curdir,"data","decomptes"), 'br') as fich:
                decompt = pickle.load(fich)
                txt = ''
            for a in decompt.keys():
                txt += f'{a} : {decompt[a]} dossiers classés<br>'
        except:# aucun dossier n'a encore été traité...
            txt = ''
        return txt

    def genere_liste_impression(self):
        """ Sous-fonction pour le menu admin : liste des boutons class_*.xml """
        list_fich = glob.glob(division_to_xml('classement_final', '*'))
        txt = ''
        if len(list_fich) > 0:
            txt = self.buttons_wrapper(\
                    'Choisissez une filière pour imprimer les fiches \
                    récapitulatives de commission',
                    list_fich)
            txt +='<h3> Les tableaux récapitulatifs sont dans le dossier \
                    "./tableaux"</h3>'
        return txt

########################################################
#####     La suite concerne les pages dossiers     #####
########################################################
    def page_dossier(self, qui, mem_scroll):
        """ construction du code html constitutif de la page dossier """
        page_content = {}
        ## entête
        page_content['title'] = f'{self.titre} - Accès {qui.get_droits()}.'
        # construire ensuite les parties dossier, action de client puis liste 
        # des dossiers;
        # La partie dossier est créée par la fonction genere_dossier; infos 
        # données par client.fichier
        dossier = Composeur.html['contenu_dossier'].format(\
                **self.genere_dossier(qui, qui.get_cand(), \
                isinstance(qui, Admin)))
        # La partie contenant les actions du client \
                # (correction, motivations, validation) est créée par la \
                # fonction genere_action;
        action_client = Composeur.html['contenu_action']\
                .format(**self.genere_action(qui, qui.get_cand()))
        # La partie liste est créée par la fonction genere_liste:
        liste = self.genere_liste(qui, mem_scroll)
        # Affichage d'un bouton RETOUR 'admin uniquement'
        visib = ''
        if isinstance(qui, Jury):
            visib = 'hidden'
        # dictionnaire directement 'digérable' par la chaîne html["MEP_DOSSIER"]
        page_content['main_content'] = Composeur.html['MEP_DOSSIER'].format(**{
            'dossier' : dossier,
            'action_client' : action_client,
            'liste' : liste,
            'script' : qui.script_dossiers,
            'visibilite' : visib
            })
        page_content['script'] = qui.script_dossiers
        # Composition de la page
        return Composeur.html["Page"].format(**page_content)

    def genere_dossier(self, qui, cand, format_admin = False):
        """ Renvoie le dictionnaire contenant les infos du dossier en cours"""
        # format_admin = False lorsque la demande est destinée à concevoir les 
        # fiches bilan de commission.  En effet, cette demande est lancée par 
        # Admin, mais l'impression se fait avec un dossier formaté comme pour 
        # Jury : les notes de sont pas des <input type="text" .../>.  C'est 
        # ensuite le code css qui se charge d'adapter l'aspect de la page pour 
        # l'impression (fond blanc, barre de correction invisible, remplacée par 
        # une indication du jury qui a traité le dossier et la correction faite, 
        # liste des dossiers également invisible; vive le css !)
        #### Début
        data = {}
        # Pédigré
        liste_attr = ['Nom', 'Prénom', 'Date de naissance', 'Établissement', \
                'Département', 'Pays', 'Num ParcoursSup', 'INE']
        for attr in liste_attr:
            data[attr] = cand.get(attr)
        # récup filiere pour connaître le chemin vers le dossier pdf (dans 
        # répertoire docs_candidats)
        # Si le fichier pdf n'existe pas, le lien pointe vers une page par 
        # défaut...
        fil = qui.fichier.filiere()
        data['ref_fich'] = os.path.join('data', 'docs_candidats', \
                f'{fil.lower()}', f'docs_{cand.get("Num ParcoursSup")}.pdf')
        if not os.path.isfile(data['ref_fich']):
            data['ref_fich'] = os.path.join('utils', 'pdf_error.html')
        # Formatage des champs de notes et de classe actuelle en fonction de 
        # format_admin En effet, Admin a la possibilité d'écrire dans ces champs 
        # alors que Jury est en lecture seule.
        formateur_clas_actu = '{}'
        formateur_note = '{note}'
        #activ = 'disabled'
        if format_admin:
            formateur_clas_actu = '<input type="text" id="Classe actuelle" \
                    name="Classe actuelle" style="font-size:100%;" value="{}"/>'
            formateur_note = '<input type="text" class="notes" id="{}" \
                    name="{}" value="{note}" onfocusout="verif_saisie()"/>'
            #activ = ''
        ### Suite de la création du dictionnaire
        # classe actuelle
        data['Classe actuelle'] = formateur_clas_actu\
                .format(cand.get('Classe actuelle'))
        # Notes
        matiere = ['Mathématiques Spécialité', 'Mathématiques Expertes', \
                'Physique-Chimie Spécialité']
        date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
        classe = ['Première', 'Terminale']
        for cl in classe:
            for mat in matiere:
                for da in date:
                    key = f'{mat} {cl} {da}'
                    data[key] = formateur_note\
                        .format(key, key, note=self.format_mark(cand.get(key)))
        # Autres notes
        liste = ['Mathématiques CPES', 'Physique/Chimie CPES', \
                'Écrit EAF', 'Oral EAF']
        for li in liste:
            if not(cand.is_cpes()) and 'cpes' in li.lower():
                data[li] = formateur_note.format(li, li, note='-')
            else:
                data[li] = formateur_note.format(li, li,\
                        note=self.format_mark(cand.get(li)))
        # Suite
        data['cand'] = cand.get('Candidatures impr')
        return data
    
    def genere_action(self, client, cand):
        """ Renvoie le dictionnaire de la partie 'action' de la page HTML"""
        ###
        # Estimation du rang final du candidat
        rg_fin = ''
        visib = 'none' # n'est visible que pour les jurys
        if isinstance(client, Jury): # seulement pour les jurys.
            rg_fin = client.get_rgfinal(cand)
            visib = '' # est visible pour les jurys
        rang_final = f'<div style = "display:{visib};">\
                Estimation du rang final : {rg_fin}</div>'
        ### Partie correction :
        # récupération correction
        cor = cand.get('Correction')
        if cor == 'NC':
            correc = min_correc # NC correspond à la correction minimale
            rg_fin = 'NC'
        else:
            # valeur numérique de la correction -> placement du curseur.
            correc = cor
        # Construction de la barre de correction qu'on alimente avec les infos 
        # courantes..
        barre = Composeur.barre.format(correc, cand.get('Jury'), cor)
        ### Partie motivations :
        motifs = Composeur.motifs.format(cand.get('Motifs'))
        # On met tout ça dans un dico data pour passage en argument à 
        # html['contenu_action']
        data = {'barre' : barre,
                'scoreb' : self.format_mark(cand.get('Score brut')),
                'scoref' : self.format_mark(cand.get('Score final')),
                'rg_fin' : str(rang_final),
                'motifs' : motifs
                }
        return data
        
    def genere_liste(self, client, mem_scroll):
        """ Génère la partie liste de la page HTML"""
        # Construction de la chaine lis : code html de la liste des dossiers.
        lis = '<form class = "col wrap" action = "click_list" method=POST>'
        lis += f'<input type="hidden" name = "scroll_mem" \
                value = "{mem_scroll}"/>'
        ## Gestion des ex-aequo (score final seulement). On va construire une 
        ## liste des scores finals concernés. Puis, dans la boucle suivante, on
        ## mettra en évidence les dossiers pour le jury...
        doublons_sf = set()
        ensemble_sf = set()
        for index, cand in enumerate(client.fichier):
            if cand.get('traité') and cand.get('Correction') != 'NC':
                sf = cand.get('Score final')
                if sf in ensemble_sf:
                    doublons_sf.add(sf)
                else:
                    ensemble_sf.add(sf)
        for index, cand in enumerate(client.fichier):
            # Les candidats rejetés par admin n'apparaissent pas aux jurys
            a = isinstance(client, Jury)
            b = cand.get('Correction') == 'NC'
            c = cand.get('Jury') == 'Admin'
            if not(a and b and c):
                lis += '<input type = "submit" name="num" '
                clas = 'doss'
                if cand == client.get_cand():
                    # affecte la class css "doss_courant" au dossier courant
                    clas += ' doss_courant'
                if cand.get('traité'):
                    # affecte la classe css "doss_traite" aux dossiers traités
                    clas += ' doss_traite'
                if cand.get('Score final') in doublons_sf:
                    # gestion ex-aequo
                    clas += ' doss_doublon_sf'
                if cand.get('Correction') == 'NC':
                    # affecte la classe css "doss_rejete" aux dossiers NC
                    clas += ' doss_rejete'
                ### dossiers à mettre en évidence (fond rouge) :
                # client Admin ET alerte déposée par nettoie_xml.py
                if isinstance(client, Admin) and '- Alerte' in cand.get('Motifs'):
                    clas += ' doss_incomplet' # TERME INCOMPLET INADÉQUAT
                # Si Admin a écrit un commentaire :
                if '- Admin' in cand.get('Motifs'):
                    if isinstance(client, Admin): # si admin
                        clas += ' doss_commente'
                    if isinstance(client, Jury): # si jury
                        clas += ' doss_incomplet' # TERME INCOMPLET INADÉQUAT
                # Si à l'EPA : un cadre de couleur pour garder la 
                # lisibilité 'traité, non-traité, rejeté'...
                if "Pupilles de l'Air" in cand.get('Établissement'):
                    clas += ' doss_epa'
                ### fin dossiers à mettre en évidence
                lis += f'class = "{clas}"'
                nom = f"{cand.get('Nom')}, {cand.get('Prénom')}"
                # La variable txt qui suit est le texte du bouton. Attention, 
                # ses 3 premiers caractères doivent être le numéro du dossier 
                # dans la liste des dossiers (client_get_dossiers())... Cela 
                # sert dans click_list(), pour identifier sur qui on a clické..  
                # une police monospace est utilisée pour l'esthétique et la 
                # largeur affectée au nom est fixée. Ainsi, les informations de 
                # candidatures multiples sont alignées.
                txt = f"{index+1:3d}) {nom[:29]: <30}{cand.get('Candidatures')}"
                lis += f' value="{txt}"></input>'
        lis += '-'*7 + ' fin de liste ' + '-'*7
        lis = lis + '</form>'
        return lis
    
##### La suite concerne les pages qu'on imprime
    def page_impression(self, qui):
        """ Fabrication de la page 'impression des fiches bilan' """
        cand = qui.get_cand()
        fich = qui.fichier
        entete = f'<h1 align="center" class="titre">{self.titre} - \
            {fich.filiere().upper()}.</h1>'
        txt = ''
        # on saute une page entre chaque candidat :
        saut = '<div style = "page-break-after: always;"></div>'
        for cand in fich:
            # récupération du contenu du fichier config.py
            nb = nb_classes[fich.filiere().lower()]
            # Si nb n'est pas convertible en un entier positif alors on classe 
            # tous les candidats
            try:
                nb_max = int(nb)
                if nb_max < 0: nb_max = len(fich)
            except:
                nb_max = len(fich)
            a = (cand.get('traité') == 'oui')
            b = (cand.get('Correction') != 'NC')
            c = not(b) or (int(cand.get('Rang final')) <= nb_max)
            if a and b and c:
                # seulement les classés dont le rang est inférieur à la limite 
                # fixée
                txt += entete
                txt += f"<div class='row bordered justAround taille1 bold'>\
                        Candidat classé : {cand.get('Rang final')}</div>"
                txt += Composeur.html['contenu_dossier']\
                        .format(**self.genere_dossier(qui, cand))
                txt += Composeur.html['contenu_action']\
                        .format(**self.genere_action(qui, cand))
                txt += saut
        # On enlève le dernier saut de page... sinon on a une page blanche !
        txt = txt[:-len(saut)]
        return Composeur.html['page_impress'].format(**{'pages' : txt}) 
