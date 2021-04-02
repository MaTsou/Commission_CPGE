from utils.candidat import *
"""Le résultat de la reconnaissance des données sur ParcoursSup est
parfois un peu brut : ce module fournit des fonctions
d'assainissement.
"""

#
# FONCTIONS DE POST-TRAITEMENT
#

# Variables globales

series_valides = ["Série Générale",
                  "Scientifique",
                  "Préparation au bac Européen"]
series_non_valides = \
    ["Sciences et Technologies de l'Industrie et du Développement Durable",
     "Economique et social",
     "Littéraire",
     "Sciences et technologie de laboratoire",
     "Professionnelle"]


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

    valids = node.xpath('synoptique/établissement/candidature_validée')
    oui = valids[0].text.lower()
    if oui != 'oui':
        commentaire = 'Candidature non validée sur ParcoursSup'
        candidat.set('Correction', 'NC')
        candidat.set('Jury', 'Admin')
    else:  # si validée,
        # on récupère la série
        serie = ''
        probs = node.xpath('bulletins/bulletin[classe="Terminale"]')
        for prob in probs:  # fausse boucle (normalement)
            serie = prob.xpath('série')[0].text
        # Si série non valide, on exclut
        if serie in series_non_valides:
            commentaire = f'Série {serie}'
            candidat.set('Correction', 'NC')
            candidat.set('Jury', 'Admin')
        else:  # sinon, on alerte Admin sur certaines anomalies rencontrées
            prefixe = '- Alerte :'
            # 1/ Série reconnue ?
            if serie not in series_valides:
                commentaire += ' | Vérifier la série |'
            # 2/ Le dossier est-il complet?
            # (toutes les notes présentes et classe actuelle correcte)
            if not candidat.is_complet():
                commentaire += ' | Dossier incomplet |'
            # 3/ Classe actuelle n'est pas Terminale
            classe = candidat.get('Classe actuelle').lower()
            if not ('terminale' in classe or 'cpes' in classe):
                commentaire += ' | Vérifier la classe actuelle |'
    if commentaire != '':
        candidat.set('Motifs', f'{prefixe} {commentaire}')
    else:  # si aucune remarque, on calcule le score brut
        candidat.update_raw_score()
    # Fin des filtres; on retourne le noeud du candidat mis à jour
    return candidat.get_node()


def repeche(node):
    # FIXME: Fonction utile en 2021 seulement
    """Pour les candidats de CPES, cette fonction reporte les notes de
    maths et physique dans les champs des spécialités correspondantes.
    Pour les candidats en terminale, reporte les notes de contrôle continu de 
    français vers les notes EAF.

    """
    # Création d'un objet candidat car on va écrire dans le noeud
    candidat = Candidat(node)

    # CPES
    # Dictionnaire source : destination
    transfert = {
            'Mathématiques Spécialité' : 'Mathématiques',
            'Physique-Chimie Spécialité' : 'Physique/Chimie',
            }

    if candidat.get('Classe actuelle').lower() == 'cpes':
        for classe in ['Première', 'Terminale']:
            for date in ['trimestre 1', 'trimestre 2', 'trimestre 3']:
                for sour,dest in transfert.items():
                    sour_value = candidat.get(f'{sour} {classe} {date}')
                    if sour_value != '-' and \
                            candidat.get(f'{dest} {classe} {date}') == '-':
                        candidat.set(f'{dest} {classe} {date}', sour_value)

    # Terminales
    if candidat.get('Classe actuelle').lower() != 'cpes' and \
            candidat.get('Écrit EAF') == '-':
        somme, coef = 0, 0
        for date in ['trimestre 1', 'trimestre 2', 'trimestre 3']:
            sour_value = candidat.get(f'Français Première {date}')
            if sour_value != '-':
                somme += float(sour_value.replace(',','.'))
                coef += 1
            if coef:
                candidat.set('Écrit EAF', str(somme/coef))
                candidat.set('Oral EAF', str(somme/coef))
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
