from lxml import etree
from utils.fichier import Fichier

# Le résultat de la reconnaissance des données sur ParcoursSup est
# parfois un peu brut : on procède à l'assainissement.

#
# FONCTIONS DE POST-TRAITEMENT
#
# Variables globales
series_valides = ["Générale", "Scientifique", "Préparation au bac Européen"]
series_non_valides = ["Sciences et Technologies de l'Industrie et du Développement Durable",
        "Economique et social", "Littéraire", "Sciences et technologie de laboratoire",
        "Professionnelle"]

# certains bulletins sont très vides : on nettoie.

def elague_bulletins_triviaux(candidat, test = False):

    # on trouve la liste des bulletins sans note:
    probs = candidat.xpath('bulletins/bulletin[matières[not(matière)]]')
    for prob in probs:
        candidat.xpath('bulletins')[0].remove(prob)

    return candidat

def filtre(candidat, test = False):
    prefixe = ''
    commentaire = ''
    # Candidature validée ?
    if candidat.xpath('synoptique/établissement/candidature_validée')[0].text.lower() != 'oui':
        commentaire = 'Candidature non validée sur ParcoursSup'
        Fichier.set(candidat, 'Correction', 'NC')
        Fichier.set(candidat, 'Jury', 'Admin')
    else: # si validée,
        # on récupère la série
        serie = ''
        probs = candidat.xpath('bulletins/bulletin[classe="Terminale"]')
        for prob in probs: # fausse boucle (normalement)
            serie = prob.xpath('série')[0].text
        # Si série non valide, on exclut
        if serie in series_non_valides:
            commentaire = 'Série {}'.format(serie)
            Fichier.set(candidat, 'Correction', 'NC')
            Fichier.set(candidat, 'Jury', 'Admin')
        else: # sinon, on alerte Admin sur certaines anomalies rencontrées
            prefixe = '- Alerte :'
            # 1/ Série reconnue ?
            if not(serie in series_valides):
                commentaire += ' | Vérifier la série |'
            # 2/ Le dossier est-il complet (toutes les notes présentes + classe actuelle)
            if not(Fichier.is_complet(candidat)):
                commentaire += ' | Dossier incomplet |'
            # 3/ Classe actuelle n'est pas Terminale
            classe = Fichier.get(candidat, 'Classe actuelle').lower()
            if not('terminale' in classe or 'cpes' in classe):
                commentaire += ' | Vérifier la classe actuelle |'
    if commentaire != '':
        Fichier.set(candidat, 'Motifs', '{} {}'.format(prefixe, commentaire))
    else: # si aucune remarque, on calcule le score brut
        Fichier.calcul_scoreb(candidat)
    # Fin des filtres; on retourne un candidat mis à jour
    return candidat

# Fonction utile en 2021 seulement : si candidat en cpes, je reporte ses notes
# de math et de phys dans les champs math spécialité et phys spécialité
def repeche(candidat, test):
    if Fichier.get(candidat, 'Classe actuelle').lower() == 'cpes':
        for cl in ['Première', 'Terminale']:
            for date in ['trimestre 1', 'trimestre 2', 'trimestre 3']:
                Fichier.set(candidat, 'Mathématiques Spécialité {} {}'.format(cl, date),\
                Fichier.get(candidat, 'Mathématiques {} {}'.format(cl, date)))
                Fichier.set(candidat, 'Physique-Chimie Spécialité {} {}'.format(cl, date),\
                Fichier.get(candidat, 'Physique/Chimie {} {}'.format(cl, date)))
    return candidat

#
# FONCTION PRINCIPALE
#

def nettoie(candidats, test = False):
    res = [elague_bulletins_triviaux(candidat, test)
           for candidat in candidats]
    res = [repeche(candidat, test) for candidat in candidats]
    res = [filtre(candidat, test) for candidat in candidats]
    return candidats
