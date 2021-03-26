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


def elague_bulletins_triviaux(candidat):
    """Supprime les bulletins vides du dossier du candidat donné"""

    probs = candidat.xpath('bulletins/bulletin[matières[not(matière)]]')
    for prob in probs:
        candidat.xpath('bulletins')[0].remove(prob)

    return candidat


def filtre(candidat):
    """Cette fonction filtre automatiquement certains candidats dont le
    dossier présente des défauts rédhibitoires pour un traitement
    automatique : il faut qu'un administrateur regarde!

    """
    prefixe = ''
    commentaire = ''

    valids = candidat.xpath('synoptique/établissement/candidature_validée')
    oui = valids[0].text.lower()
    if oui != 'oui':
        commentaire = 'Candidature non validée sur ParcoursSup'
        candidat.set('Correction', 'NC')
        candidat.set('Jury', 'Admin')
    else:  # si validée,
        # on récupère la série
        serie = ''
        probs = candidat.xpath('bulletins/bulletin[classe="Terminale"]')
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
        candidat.update_brut_score()
    # Fin des filtres; on retourne un candidat mis à jour
    return candidat


def repeche(candidat):
    # FIXME: Fonction utile en 2021 seulement
    """Pour les candidats de CPES, cette fonctions reporte les notes de
    maths et physique dans les champs des spécialités correspondantes.

    """

    if candidat.get('Classe actuelle').lower() == 'cpes':
        for classe in ['Première', 'Terminale']:
            for date in ['trimestre 1', 'trimestre 2', 'trimestre 3']:
                candidat.set(f'Mathématiques Spécialité {classe} {date}',
                             candidat.get(f'Mathématiques {classe} {date}'))
                candidat.set(f'Physique-Chimie Spécialité {classe} {date}',
                             candidat.get(f'Physique/Chimie {classe} {date}'))
    return candidat

#
# FONCTION PRINCIPALE
#


def nettoie(candidats):
    """Cette fonction appelle successivement toutes les fonctions de
    nettoyage"""
    _ = [elague_bulletins_triviaux(candidat)
         for candidat in candidats]
    _ = [repeche(candidat) for candidat in candidats]
    _ = [filtre(candidat) for candidat in candidats]
    return candidats
