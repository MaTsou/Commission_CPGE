from utils.candidat import *
"""Le résultat de la reconnaissance des données sur ParcoursSup est
parfois un peu brut : ce module fournit des fonctions
d'assainissement.
"""

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
     "Formations des écoles d'ingénieurs",
     "Formations d'architecture, du paysage et du patrimoine",
     "Autre formation du supérieur",
     "PACES (Médecine, Pharmacie, Sage femme, Dentiste, Kiné"]

def exclure_candidature(cand, motif):
    cand.set('Correction', 'NC')
    cand.set('Jury', 'Admin')
    cand.set('Motifs', motif)

def get_serie(node):
    serie = ''
    probs = node.xpath('bulletins/bulletin[classe="Terminale"]')
    for prob in probs:  # fausse boucle (normalement)
        serie = prob.xpath('série')[0].text
    return serie

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
    candidat = Candidat(node)

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
    prefixe = '- Alerte :' # indicateur d'une alerte
    commentaire = [] # reçoit les différents commentaires

    # 1/ Série reconnue comme valide ?
    if serie not in series_valides:
        commentaire.append('Vérifier la série')

    # 2/ Le dossier est-il complet?
    # (toutes les notes présentes et classe actuelle correcte)
    if not candidat.is_complet():
        commentaire.append('Dossier incomplet')

    # 3/ Classe actuelle non reconnue ?
    if classe_actuelle not in classes_actuelles_valides:
        commentaire.append('Vérifier la classe actuelle')

    # Insertion de l'alerte dans le dossier candidat
    if len(commentaire):
        commentaires = ' | '.join(commentaire)
        candidat.set('Motifs', f'{prefixe} {commentaires}')
    else:  # si aucune remarque, on calcule le score brut
        candidat.update_raw_score()
    # Fin des filtres; on retourne le noeud du candidat mis à jour
    return candidat.get_node()


def repeche(node):
    # FIXME: Fonction utile en 2021 seulement
    """Pour les candidats de CPES, cette fonction reporte les notes de
    maths et physique dans les champs des spécialités correspondantes.

    """
    # Création d'un objet candidat car on va écrire dans le noeud
    candidat = Candidat(node)

    # CPES
    # Dictionnaire source : destination
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
