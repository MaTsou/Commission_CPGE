from lxml import etree
import utils.interface_xml as xml

# Le résultat de la reconnaissance des données sur ParcoursSup est
# parfois un peu brut : on procède à l'assainissement.

#
# FONCTIONS DE POST-TRAITEMENT
#
# Variables globales
series_valides = ['Scientifique', 'Préparation au bac Européen']

# certains bulletins contiennent toutes les notes et l'année, la
# plupart tout le bulletin sauf les notes ; il faut donc trouver les
# notes et les déplacer où on veut.

def fusionne_bulletins(candidat, test = False):

    # on trouve la liste des bulletins sans note:
    probs = candidat.xpath('bulletins/bulletin[matières[not(matière)]]')
    for prob in probs:
        # là, normalement, c'est une fausse boucle : on ne devrait avoir
        # qu'une année!
        for node in prob.xpath('année'):
            annee = node.text
            autres = candidat.xpath('bulletins/bulletin[année = "{0:s}"]'.format(annee))
            autres.remove(prob)
            # ok, on a tous les doublons maintenant (normalement: 0 ou 1)
            for doublon in autres:
                prob.xpath('matières')[0].extend(doublon.xpath('matières/matière'))
                candidat.xpath('bulletins')[0].remove(doublon)

    return candidat

def filtre(candidat, test = False):
    prefixe = ''
    commentaire = ''
    # Candidature validée ?
    if candidat.xpath('synoptique/établissement/candidature_validée')[0].text != 'Oui':
        commentaire = 'Candidature non validée sur ParcoursSup'
        xml.set_correc(candidat, 'NC')
    else: # si validée, on signale les anomalies à l'admin
        prefixe = '- Alerte :'
        # 1/ Est-ce la bonne série ?
        probs = candidat.xpath('bulletins/bulletin[classe="Terminale"]')
        for prob in probs:
            # Là, normalement, c'est une fausse boucle
            if not(prob.xpath('série')[0].text in series_valides):
                commentaire += ' | Vérifier la série |'
        # 2/ Le dossier est-il complet (toutes les notes présentes + classe actuelle)
        if not(xml.is_complet(candidat)):
            commentaire += ' Dossier incomplet |'
    if commentaire != '':
        xml.set_motifs(candidat, '{} {}'.format(prefixe, commentaire))
    # Fin des filtres; on retourne un candidat mis à jour
    return candidat


#
# FONCTION PRINCIPALE
#

def nettoie(candidats, test = False):
    res = [fusionne_bulletins(candidat, test)
           for candidat in candidats]
    res = [filtre(candidat, test) for candidat in candidats]
    return candidats
