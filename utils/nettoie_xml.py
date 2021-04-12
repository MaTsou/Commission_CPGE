from utils.candidat import *
import os, logging
"""Le résultat de la reconnaissance des données sur ParcoursSup est
parfois un peu brut : ce module fournit des fonctions
d'assainissement.
"""

# Création d'un journal de log
formatter = logging.Formatter(\
        "%(levelname)s :: %(message)s")
# Qui récupère les messages ? (on peut en définir plusieurs)
handler = logging.FileHandler(os.path.join("utils", "logs", \
        "journal_nettoie.log"), mode="a", encoding="utf-8")
handler.setFormatter(formatter)
# L'objet appelé par tout élément du programme qui veut journaliser qqc
journal = logging.getLogger("nettoie_xml")
journal.addHandler(handler)
#
# FONCTIONS DE POST-TRAITEMENT
#

# Variables globales

series_valides = \
    ["Série Générale",
     "Scientifique",
     "Préparation au bac Européen"]

series_non_valides = \
    ["Sciences et Technologies de l'Industrie et du Développement Durable",
     "Economique et social",
     "Littéraire",
     "Sciences et technologie de laboratoire",
     "Professionnelle"]

classes_actuelles_valides = ["Terminale", "CPES"]

classes_actuelles_non_valides = \
    ["CPGE",
     "Licence",
     "Licence sélective",
     "DUT",
     "Formations des écoles d'ingénieurs",
     "Formations d'architecture, du paysage et du patrimoine",
     "Autre formation du supérieur",
     "PACES (Médecine, Pharmacie, Sage femme, Dentiste, Kiné"]

def exclure_candidature(cand, motif):
    cand.set('Correction', 'NC')
    cand.set('Jury', 'Admin')
    cand.set('Motifs', motif)
    journal.critical(f"{cand.get('Nom')} {cand.get('Prénom')} : {motif}")

def get_serie(node):
    serie = ''
    probs = node.xpath('bulletins/bulletin[classe="Terminale"]')
    for prob in probs:  # fausse boucle (normalement)
        serie = prob.xpath('série')[0].text
    return serie

def filtre_eds(node):
    # les enseignements de spécialité conviennent-ils ?
    eds_requises = {'Mathématiques Spécialité','Physique-Chimie Spécialité'}
    eds_candidat = set()
    # eds de terminale
    probs = node.xpath('synoptique/enseignement_de_specialite_terminale')
    for prob in probs:  # on récupère tous les eds
        eds_candidat.add(prob.text)
    if not eds_requises.issubset(eds_candidat):
        return 'Enseignements de Spécialité inadéquats (classe de terminale)'

    eds_candidat = set()
    # eds de première
    probs = node.xpath('synoptique/enseignement_de_specialite_premiere')
    for prob in probs:  # on récupère tous les eds
        eds_candidat.add(prob.text)
    if not eds_requises.issubset(eds_candidat):
        return 'Enseignements de Spécialité inadéquats (classe de première)'
    return False

def elague_bulletins_triviaux(node):
    """Supprime les bulletins vides du dossier du candidat donné"""

    probs = node.xpath('bulletins/bulletin[matières[not(matière)]]')
    for prob in probs:
        node.xpath('bulletins')[0].remove(prob)

    return node


def filtre(node):
    """Cette fonction filtre automatiquement certains candidats dont le
    dossier présente des défauts rédhibitoires pour un traitement
    automatique : il faut qu'un administrateur regarde!

    """
    prefixe = ''
    commentaire = ''
    # Création d'un objet candidat car on va écrire dans le noeud
    candidat = Candidat(node, journal)

    # La candidature est-elle validée ?
    valids = node.xpath('synoptique/candidature_validée')
    oui = valids[0].text.lower()
    if oui != 'oui':
        exclure_candidature(candidat, 'Candidature non validée sur ParcoursSup')
        return candidat.get_node()

    # la classe actuelle convient-elle ?
    classe_actuelle = candidat.get('Classe actuelle')
    if classe_actuelle in classes_actuelles_non_valides:
        exclure_candidature(candidat, 'Classe actuelle inadéquate')
        return candidat.get_node()

    # la série convient-elle ?
    serie = get_serie(node)
    # Si série non valide, on exclut
    if serie in series_non_valides:
        exclure_candidature(candidat, 'Série inadéquate')
        return candidat.get_node()

    # Si on arrive là, c'est une candidature a priori recevable. On va indiquer 
    # à l'admin les dossiers qui nécessitent son regard (anomalies)
    #
    # On va tester également les enseignements de spécialité. Il faut veiller à 
    # ce que l'éventuel rejet d'un dossier ne soit pas dû à un problème 
    # d'identification. Seuls les dossiers de candidats dans une série reconnue, 
    # et étant en terminale FIXME (cpes aussi à partir de 2022) peuvent être 
    # rejetés pour cette raison.
    prefixe = '- Alerte :' # indicateur d'une alerte
    commentaire = [] # reçoit les différents commentaires

    # enseignements de spécialité ok ?
    wrong_eds = filtre_eds(node)

    # 1/ Série reconnue comme valide ?
    if serie not in series_valides:
        commentaire.append('Vérifier la série')
        wrong_eds = False

    # 2/ Le dossier est-il complet?
    # (toutes les notes présentes et classe actuelle correcte)
    if not candidat.is_complet():
        commentaire.append('Dossier incomplet')

    # 3/ Classe actuelle non reconnue ?
    if classe_actuelle not in classes_actuelles_valides:
        commentaire.append('Vérifier la classe actuelle')
        wrong_eds = False

    # Traitement
    # on exclut si mauvais enseignements de spé
    if wrong_eds and not candidat.is_cpes(): # FIXME test cpes only en 2021
        exclure_candidature(candidat, wrong_eds)
    else:
        # Insertion de l'éventuelle alerte dans le dossier candidat
        if len(commentaire):
            commentaires = ' | '.join(commentaire)
            candidat.set('Motifs', f'{prefixe} {commentaires}')
        else:  # si aucune remarque :
            candidat.update_raw_score()
    # Fin des filtres; on retourne le noeud du candidat mis à jour
    return candidat.get_node()


def repeche(node):
    # FIXME: Fonction utile en 2021 seulement
    """Pour les candidats de CPES, cette fonction reporte les notes de
    maths et physique dans les champs des spécialités correspondantes.

    """
    # Création d'un objet candidat car on va écrire dans le noeud
    candidat = Candidat(node, journal)

    # CPES
    # Dictionnaire destination : source 
    transfert = {
            'Mathématiques Spécialité' : 'Mathématiques',
            'Physique-Chimie Spécialité' : 'Physique/Chimie',
            }

    if candidat.is_cpes():
        for classe in ['Première', 'Terminale']:
            for date in ['trimestre 1', 'trimestre 2', 'trimestre 3']:
                for dest,sour in transfert.items():
                    sour_value = candidat.get(f'{sour} {classe} {date}')
                    if sour_value != '-' and \
                            candidat.get(f'{dest} {classe} {date}') == '-':
                        candidat.set(f'{dest} {classe} {date}', sour_value)
    return candidat.get_node()

#
# FONCTION PRINCIPALE
#


def nettoie(xml_nodes):
    """Cette fonction appelle successivement toutes les fonctions de
    nettoyage"""
    _ = [elague_bulletins_triviaux(node) for node in xml_nodes]
    _ = [repeche(node) for node in xml_nodes]
    _ = [filtre(node) for node in xml_nodes]
    return xml_nodes
