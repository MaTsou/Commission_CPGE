#!/usr/bin/env python3
#-*- coding: utf-8 -*-

# Ce fichier contient la classe Composeur
#   Contient tout ce qui sert à composer le code html; renvoie
#   une page html à destination de navigateur.

import os, sys, glob, pickle
import utils.interface_xml as xml
import utils.boite_a_outils as outil
from utils.parametres import filieres
from utils.parametres import min_correc
from utils.parametres import max_correc
from utils.parametres import nb_correc
from utils.parametres import motivations
from utils.parametres import nb_classes
from utils.classes import Fichier, Jury, Admin

#################################################################################
#                               Composeur                                       #
#################################################################################
class Composeur(object):
    """Composeur de pages html. Lui sont donnés, un objet client, un type de page
    (menu ou traitement), éventuellement un candidat ou toute autre information
    utile (statistiques, ..)"""

    ### Attributs de classe
    # Chargement de tous les "patrons" de pages HTML dans le dictionnaire "html" :
    with open(os. path. join(os.curdir, "utils", "patrons.html"), "r", encoding="utf8") as fi:
        html = {}
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

    # corrections proposées aux jurys (faire attention que 0 soit dans la liste !!)
    corrections = [(n+min_correc*nb_correc)/float(nb_correc) for n in range(0, (max_correc-min_correc)*nb_correc+1)]
    ### Fin déclaration attributs de classe

    # constructeur
    def __init__(self, titre):
        # Variable d'instance : entête des pages html générées.
        self.titre = titre

    # Méthodes
    def genere_entete(self, titre):
        page = '<!DOCTYPE html><html>'
        page += Composeur.html['Entete'].format(**{'titre' : titre})
        return page

##### Ici commence ce qui concerne les pages menus #####

    def menu(self, qui = None, fichiers_utilises = None, comm_en_cours = False): 
        # compose le menu du client 'qui'
        # fichiers_utilises est une liste qui contient les fichiers déjà
        # choisis par un jury. Permet d'éviter que deux jurys travaillent
        # sur un même fichier.
        # comm_en_cours est un booléen qui permet d'adapter le menu de
        # l'administrateur lorsque la commission se déroule.
        if qui:
            if isinstance(qui, Admin):
                return self.menu_admin(qui, fichiers_utilises, comm_en_cours)
            else:
                return self.menu_comm(qui, fichiers_utilises)
        else: # qui = None, application lancée en mode test
            page = self.genere_entete('{}.'.format(self.titre))
            page += Composeur.html['PageAccueil']
            page += '</html>'
            return page # menu 'TEST' : admin ou jury ?

    def menu_comm(self, qui, fichiers_utilises):
        # compose le menu du jury 'qui'
        # Fichiers utilisés est une liste des fichiers déjà choisis par un jury
        # Ces fichiers sont inaccessibles (bouton disabled dans genere_menu_comm)
        ## entête
        page = self.genere_entete('{} - Accès {}.'.format(self.titre, qui.get_droits()))
        ## Contenu = liste de fichiers
        txt = ''
        # Recherche des fichiers destinés à la commission
        list_fich = glob.glob(os.path.join(os.curdir, "data", "comm_*.xml"))
        txt = ''
        # Chaque fichier apparaîtra sous la forme d'un bouton
        for fich in list_fich:
            txt += '<input type="submit" class = "fichier" name="fichier" value="{}"'.format(fich)
            # Si un fichier est déjà traité par un autre jury, son bouton est disabled...
            if fich in fichiers_utilises:
                txt += ' disabled'
            txt += '/><br>'
        # On n'affiche le texte ci-dessous que s'il y a des fichiers à traiter.
        if txt != '':
            txt = '<h2>Veuillez sélectionner le fichier que vous souhaitez traiter.</h2>' + txt
        ## Fabrication de la page
        contenu = Composeur.html["menu_comm"].format(**{'liste' : txt})
        page += Composeur.html["MEP_MENU"].format(**{'contenu' : contenu})
        page += '</html>'
        return page

    # Ci-après, ce qui concerne LES menus administrateur
    def menu_admin(self, qui, fichiers_utilises, comm_en_cours):
        # Compose le menu administrateur
        data = {}
        ## entête
        page = self.genere_entete('{} - Accès {}.'.format(self.titre, qui.get_droits()))
        ## contenu : selon l'état (phase 1, 2 ou 3) du traitement
        # phase 1 : avant la commission, l'admin gère ce qui provient de ParcoursSup,
        #           commente et/ou complète les dossiers
        # phase 2 : l'admin a généré les fichiers *_comm_* destinés à la commission. Les
        #           différents jurys doivent se prononcer sur les dossiers. C'est le coeur
        #           de l'opération de sélection.
        # phase 3 : commission terminée. L'admin doit gérer "l'après sélection" : recomposer
        #           un fichier ordonné par filière, générer tous les tableaux récapitulatifs.
        if comm_en_cours: # attention, n'est jamais 'True' si le serveur fonction en localhost
            pass
        else:
            list_fich_comm = glob.glob(os.path.join(os.curdir,"data","comm_*.xml"))
            patron = 'menu_admin_'
            if len(list_fich_comm) > 0: # phase 3 (ou entre 1 et 2, si l'admin s'amuse en localhost!)
                patron += 'apres'
                # Etape 4 bouton
                data['bout_etap4'] = '<input type = "button" class ="fichier"'
                data['bout_etap4'] += ' value = "Récolter les fichiers" onclick = "recolt_wait();"/>'
                data['decompt'] = self.genere_liste_decompte()
                data['liste_stat'] = self.genere_liste_stat()
                # Etape 5 bouton et Etape 6
                list_fich_class = glob.glob(os.path.join(os.curdir,"data","class_*.xml"))
                txt5 = ''
                txt6 = ''
                if len(list_fich_class) > 0:
                    txt5 = self.genere_liste_impression()
                data['liste_impression'] = txt5
            
            else: # avant commission
                patron += 'avant'
                # liste csv
                data['liste_csv'] = self.genere_liste_csv()
                # liste pdf
                data['liste_pdf'] = self.genere_liste_pdf()
                # liste admin
                data['liste_admin'] = self.genere_liste_admin()
                # liste_stat
                data['liste_stat'] = self.genere_liste_stat()
                # Etape 3 bouton : ce bouton n'est actif que si admin a levé toutes les alertes.
                txt = ''
                ### Teste s'il reste encore des alertes dans les fichiers admin
                # Récupération des fichiers admin
                list_fich = {Fichier(fich) for fich in glob.glob(os.path.join(os.curdir, "data", "admin_*.xml"))}
                alertes = False
                while not(alertes) and len(list_fich) > 0:
                    fich = list_fich.pop()
                    alertes = ( True in {'- Alerte :' in xml.get(cand, 'Motifs') for cand in fich} )
                ### Suit
                if len(self.genere_liste_admin()) > 0:
                    txt = '<input type = "button" class ="fichier" value = "Générer les fichiers commission"'
                    affich = ''
                    if (alertes):
                        affich = 'disabled'
                    txt += 'onclick = "genere_wait();" {}/>'.format(affich)
                data['bout_etap3'] = txt
            # Envoyez le menu
            contenu = Composeur.html[patron].format(**data)
        # Composition de la page
        page += Composeur.html["MEP_MENU"].format(**{'contenu' : contenu})
        page += '</html>'
        return page
    
    def genere_liste_csv(self):
        # Sous-fonction pour le menu admin
        txt = ''
        for fich in glob.glob(os.path.join(os.curdir,"data","*.csv")):
            txt += '{}<br>'.format(fich)
        return txt
    
    def genere_liste_pdf(self):
        # Sous-fonction pour le menu admin
        txt = ''
        for fich in glob.glob(os.path.join(os.curdir,"data","*.pdf")):
            txt += '{}<br>'.format(fich)
        return txt
    
    def genere_liste_admin(self):
        # Sous-fonction pour le menu admin
        list_fich = glob.glob(os.path.join(os.curdir,"data","admin_*.xml"))
        txt = ''
        if len(list_fich) > 0:
            txt = '<h2>Choisissez le fichier que vous souhaitez compléter</h2>'
        for fich in list_fich:
            txt += '<input type="submit" class = "fichier" name="fichier" value="{}"/>'.format(fich)
            txt += '<br>'
        return txt
    
    def genere_liste_stat(self):
        # Sous-fonction pour le menu admin
        liste_stat = ''
        if len(glob.glob(os.path.join(os.curdir,"data","admin_*.xml"))) > 0: # si les fichiers admin existent
            # lecture du fichier stat
            try:
                with open(os.path.join(os.curdir, "data", "stat"), 'br') as fich:
                    stat = pickle.load(fich)
            except: # stat n'existe pas
                outils.stat() # on le créé
                with open(os.path.join(os.curdir, "data", "stat"), 'br') as fich:
                    stat = pickle.load(fich)
            # Création de la liste
            liste_stat = '<h4>Statistiques :</h4>'
            # Pour commencer les sommes par filières
            liste_stat += '<ul style = "margin-top:-5%">'
            deja_fait = [0] # sert au test ci-dessous si on n'a pas math.log2()
            for i in range(len(filieres)):
                liste_stat += '<li>{} dossiers {} validés</li>'.format(stat[2**i], filieres[i].upper())
                deja_fait.append(2**i)
            # Ensuite les requêtes croisées
            liste_stat += 'dont :<ul>'
            for i in range(2**len(filieres)):
                if not(i in deja_fait):  # avec la fonction math.log2 ce test est facile !!!
                    seq = []
                    bina = bin(i)[2:] # bin revoie une chaine qui commence par 'Ob' : on vire !
                    while len(bina) < len(filieres):
                        bina = '0{}'.format(bina) # les 0 de poids fort sont restaurés
                    for char in range(len(bina)):
                        if bina[char] == '1':
                            seq.append(filieres[len(filieres)-char-1].upper())
                    txt = ' + '.join(seq)
                    liste_stat += '<li>{} dossiers {}</li>'.format(stat[i], txt)
            liste_stat += '</ul></ul>'
        return liste_stat

    def genere_liste_decompte(self):
        # Sous-fonction pour le menu admin (pendant commission)
            try:
                with open(os.path.join(os.curdir,"data","decomptes"), 'br') as fich:
                    decompt = pickle.load(fich)
                    txt = ''
                for a in decompt.keys():
                    txt += '{} : {} dossiers classés<br>'.format(a, decompt[a])
            except:# aucun dossier n'a encore été traité...
                txt = ''
            return txt

    def genere_liste_impression(self):
        # Sous-fonction pour le menu admin
        list_fich = glob.glob(os.path.join(os.curdir,"data","class_*.xml"))
        txt = ''
        if len(list_fich) > 0:
            txt = '<h2>Choisissez le fichier que vous souhaitez imprimer</h2>'
        for fich in list_fich:
            txt+= '<input type = "submit" class ="fichier" name = "fichier" value = "{}"/>'.format(fich)
            txt+='<br>'
        txt+='<h3> Les tableaux récapitulatifs sont dans le dossier "./tableaux"</h3>'
        return txt

##### La suite concerne les pages dossiers #####
    def page_dossier(self, qui, mem_scroll):
        # construction du code html constitutif de la page dossier
        # format_comm = True lorsque la demande est destinée à concevoir les fiches bilan de commission.
        # En effet, cette demande est lancée par Admin, mais l'impression se fait avec un dossier formaté
        # comme pour Jury : les notes de sont pas des <input type="text" .../>
        ## entête
        page = self.genere_entete('{} - Accès {}.'.format(self.titre, qui.get_droits()))
        # construire ensuite la partie dossier, action de client puis la partie liste;
        # La partie dossier est créée par la fonction genere_dossier; infos données par client.fichier
        dossier = Composeur.html['contenu_dossier'].format(\
                **self.genere_dossier(qui, qui.get_cand(), isinstance(qui, Admin)))
        # La partie contenant les actions du client (correction, motivations, validation)
        # est créée par la fonction genere_action;
        action_client = Composeur.html['contenu_action'].format(**self.genere_action(qui, qui.get_cand()))
        # La partie liste est créée par la fonction genere_liste:
        liste = self.genere_liste(qui, mem_scroll)
        # Affichage d'un bouton RETOUR 'admin uniquement'
        visib = ''
        if isinstance(qui, Jury):
            visib = 'none'
        # dictionnaire directement 'digérable' par la chaîne html["MEP_DOSSIER"]
        page += Composeur.html['MEP_DOSSIER'].format(**{
            'dossier' : dossier,
            'action_client' : action_client,
            'liste' : liste,
            'visibilite' : visib
            })
        page += '</html>'
        return page

    def genere_dossier(self, qui, cand, format_admin = False):
        """ Renvoie le dictionnaire contenant les infos du dossier en cours"""
        #### Début
        # Pédigré
        data = {'Nom':xml.get(cand, 'Nom') + ', ' + xml.get(cand, 'Prénom')}
        data['Date de naissance'] = xml.get(cand, 'Date de naissance')
        etab = xml.get(cand, 'Établissement')
        dep = xml.get(cand, 'Département')
        pays = xml.get(cand, 'Pays')
        data['etab'] = '{} ({}, {})'.format(etab, dep, pays)
        txt = '[{}]-{}'.format(xml.get(cand, 'Num ParcoursSup'), xml.get(cand, 'INE'))
        data['id'] = txt
        # récup filiere pour connaître le chemin vers le dossier pdf (dans répertoire docs_candidats)
        fil = qui.fichier.filiere()
        data['ref_fich'] = os.path.join('docs_candidats', '{}'.format(fil.lower()),
                'docs_{}'.format(xml.get(cand, 'Num ParcoursSup')))
        # Formatage des champs de notes et de classe actuelle en fonction du client (ou de format_comm)
        # et formatage des cases à cocher semestres (actives ou non).
        # En effet, Admin a la possibilité d'écrire dans ces champs alors que Jury est en lecture seule.
        formateur_clas_actu = '{}'
        formateur_note = '{note}'
        visib = 'disabled'
        if format_admin:
            formateur_clas_actu = '<input type="text" id="Classe actuelle" name="Classe actuelle" size="10" value="{}"/>'
            formateur_note = '<input type="text" class="notes grossi" id="{}" name="{}" value="{note}"\
                    onfocusout="verif_saisie()"/>'
            visib = ''
        ### Suite de la création du dictionnaire
        # classe actuelle
        data['Classe actuelle'] = formateur_clas_actu.format(xml.get(cand, 'Classe actuelle'))
        # cases à cocher semestres
        if xml.get(cand, 'sem_prem') == 'on': txt = 'checked'
        data['sem_prem'] = '{} {}'.format(visib, txt)
        if xml.get(cand, 'sem_term') == 'on': txt = 'checked'
        data['sem_term'] = '{} {}'.format(visib, txt)
        # Notes
        matiere = ['Mathématiques', 'Physique/Chimie']
        date = ['trimestre 1', 'trimestre 2', 'trimestre 3']
        classe = ['Première', 'Terminale']
        for cl in classe:
            for mat in matiere:
                for da in date:
                    key = '{} {} {}'.format(mat, cl, da)
                    key_script = '{}{}{}'.format(cl[0], mat[0], da[-1])
                    data[key_script] = formateur_note.format(key_script, key_script, note=xml.get(cand, key))
        # Autres notes
        liste = ['Mathématiques CPES', 'Physique/Chimie CPES', 'Écrit EAF', 'Oral EAF']
        for li in liste:
            if not('cpes' in xml.get(cand, 'Classe actuelle').lower()) and 'cpes' in li.lower():
                data[li] = formateur_note.format(li, li, note='-')
            else:
                data[li] = formateur_note.format(li, li, note=xml.get(cand, li))
        # Suite
        data['cand'] = xml.get(cand, 'Candidatures impr')
        return data
    
    def genere_action(self, client, cand):
        """ Renvoie le dictionnaire de la partie 'action' de la page HTML"""
        ###
        # Estimation du rang final du candidat
        rg_fin = ''
        visib = 'none' # n'est visible que pour les jurys
        if isinstance(client, Jury): # seulement pour les jurys.
            rg_fin = client.get_rgfinal(cand)
            visib = '' # n'est visible que pour les jurys
        ### Partie correction :
        # récupération correction
        correc = str(xml.get(cand, 'Correction'))
        ncval = ''
        if correc == 'NC':
            correc = 0
            ncval = 'NC'
            rg_fin = 'NC'
        # Construction de la barre de correction :
        barre = '<tr><td width = "2.5%"></td><td>'
        barre += '<input type = "range" class = "range" min="-3" max = "3" step = ".25" name = "correc" id = "correc"\
        onchange="javascript:maj_note();" onmousemove="javascript:maj_note();" onclick="click_range();" value =\
        "{}"/>'.format(correc)
        barre += '</td><td width = "2.5%"></td></tr>' # fin de la ligne range
        txt = '' # on construit maintenant la liste des valeurs...
        for index, valeur in enumerate(Composeur.corrections):
            if (index % 2 == 0):
                txt += '<td width = "7%">{:+3.1f}</td>'.format(valeur)
        barre += '<tr><td align = "center" colspan = "3"><table width = "100%"><tr class =\
        "correc_notimpr">{}</tr></table>'.format(txt)
        barre += '<span class = "correc_impr">'+xml.get(cand, 'Jury')+' : {:+.2f}'.format(float(correc))+'</span>'
        barre += '</td></tr>'
        ### Partie motivations :
        # Construction de la chaine motifs.
        # le premier motif : champ texte.
        motifs = '<tr><td align = "left">'
        motifs += '<input type="text" class = "txt_motifs" name="motif"\
                id = "motif" value= "{}"/>'.format(xml.get(cand, 'Motifs'))
        motifs += '</td></tr>'
        # La suite : motifs pré-définis
        for index, motif in enumerate(motivations):
            key = 'mot_' + str(index)
            motifs += '<tr><td align = "left"><input type="button" name="{}"'.format(key)
            motifs += ' id="{}" onclick="javascript:maj_motif(this.id)"'.format(key)
            motifs += ' class = "motif" value ="{}"/></td></tr>'.format(motif)
        # input hidden nc
        # Un champ caché qui sert à stocker le choix 'NC'; champ nécessaire au script.js qui surveille
        # que le jury motive bien ce genre de choix. Pourrait être remplacer par une case à cocher. On
        # supprimerait alors le bouton NC...
        nc = '<input type="hidden" id = "nc" name = "nc" value = "{}"/>'.format(ncval)
        # On met tout ça dans un dico data pour passage en argument à html['contenu_action']
        data = {'barre' : barre}
        data['scoreb'] = xml.get(cand, 'Score brut')
        data['scoref'] = xml.get(cand, 'Score final')
        data['nc'] = nc
        data['rg_fin'] = '<td style = "display:{};">Estimation du rang final : {}</td>'.format(visib, rg_fin)
        data['motifs'] = motifs
        return data
        
    def genere_liste(self, client, mem_scroll):
        """ Génère la partie liste de la page HTML"""
        # Construction de la chaine lis : code html de la liste des dossiers.
        lis = '<form id = "form_liste" action = "click_list" method=POST>'
        lis += '<input type="hidden" name = "scroll_mem" value = "{}"/>'.format(mem_scroll)
        for index, cand in enumerate(client.fichier):
            # Les candidats rejetés par admin n'apparaissent pas aux jurys
            if not(isinstance(client, Jury) and xml.get(cand, 'Correction') == 'NC' and '- Admin' in xml.get(cand, 
                'Motifs')):
                lis += '<input type = "submit" name="num" '
                clas = 'doss'
                if cand == client.get_cand(): # affecte la class css "doss_courant" au dossier courant
                        clas += ' doss_courant'
                if xml.get(cand, 'traité'):
                        clas += ' doss_traite' # affecte la classe css "doss_traite" aux dossiers qui le sont
                if xml.get(cand, 'Correction') == 'NC':
                    clas += ' doss_rejete' # affecte la classe css "doss_rejete" aux dossiers NC
                if isinstance(client, Admin) and '- Alerte' in xml.get(cand, 'Motifs'): # Admin seulement (alertes nettoie.py)
                    clas += ' doss_incomplet' # LE TERME INCOMPLET N'EST PLUS ADÉQUAT
                if isinstance(client, Jury) and '- Admin' in xml.get(cand, 'Motifs'): # Jury seulement (commentaires Admin)
                    clas += ' doss_incomplet' # LE TERME INCOMPLET N'EST PLUS ADÉQUAT
                lis += 'class = "{}"'.format(clas)
                nom = '{}, {}'.format(xml.get(cand, 'Nom'), xml.get(cand, 'Prénom'))
                # La variable txt qui suit est le texte du bouton. Attention, ses 3 premiers
                # caractères doivent être le numéro du dossier dans la liste des
                # dossiers (client_get_dossiers())... Cela sert dans click_list(), pour identifier sur qui on a clické..
                txt = '{:3d}) {: <30}{}'.format(index+1, nom[:29], xml.get(cand, 'Candidatures'))
                lis += ' value="{}"></input><br>'.format(txt)
        lis += '-'*7 + ' fin de liste ' + '-'*7
        lis = lis + '</form>'
        return lis
    
##### La suite concerne les pages qu'on imprime
    def page_impression(self, qui):
        cand = qui.get_cand()
        entete = '<h1 align="center" class="titre">{} - {}.</h1>'.format(self.titre, qui.fichier.filiere().upper())
        txt = ''
        saut = '<div style = "page-break-after: always;"></div>'
        for cand in qui.fichier:
            a = (xml.get(cand, 'Score final') != 'NC')
            b = not(a) or (int(xml.get(cand, 'Rang final')) <= int(nb_classes[qui.fichier.filiere().lower()]))
            if a and b:
                txt += entete
                txt += '<div class = encadre>Candidat classé : {}</div>'.format(xml.get(cand, 'Rang final'))
                txt += Composeur.html['contenu_dossier'].format(**self.genere_dossier(qui, cand))
                txt += Composeur.html['contenu_action'].format(**self.genere_action(qui, cand))
                txt += saut
        txt = txt[:-len(saut)] # On enlève le dernier saut de page...
        return Composeur.html['page_impress'].format(**{'pages' : txt}) 
