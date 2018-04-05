from lxml import etree

# Le résultat de la reconnaissance des données sur ParcoursSup est
# parfois un peu brut : on procède à l'assainissement.

#
# FONCTIONS DE POST-TRAITEMENT
#

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

#
# FONCTION PRINCIPALE
#

def nettoie(candidats):
    res = [fusionne_bulletins(candidat, test)
           for candidat in candidats]
    return res
