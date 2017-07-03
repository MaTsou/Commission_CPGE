from .epa_commun import annee_terminale, annee_premiere

# JP: je suis paranoïaque -- déformation professionnelle!
def verifie_entier(chaine, mini=0, maxi=20):
    res = []
    try:
        val = int(chaine)
        if not (val >= mini and val <= maxi):
            res.append("{0:d} n'est pas entre {1:s} et {2:s}".format(val, mini, maxi))
    except:
        res.append("{0:s} n'est pas un entier".format(chaine))
    return res

def verifie_flottant(chaine, mini=0, maxi=20):
    res = []
    try:
        val = float(chaine.replace(',', '.'))
        if not (val >= mini and val <= 20):
            res.append("{0:f} n'est pas entre {1:s} et {2:s}".format(val, mini, maxi))
    except:
        res.append("{0:s} n'est pas un flottant".format(chaine))
    return res

def verifie_valeurs_numeriques(candidat, dur=False):
    res = []
    synoptique = candidat.xpath('synoptique')
    if synoptique != []:
        synoptique = synoptique[0]
        fr_ecrit = synoptique.xpath('français.écrit')
        if fr_ecrit != []:
            res.extend("La note d'écrit en français {0:s}".format(pb) for pb in verifie_entier(fr_ecrit[0].text))
        fr_oral = synoptique.xpath('français.oral')
        if fr_oral != []:
            res.extend("La note d'oral en français {0:s}".format(pb) for pb in verifie_entier(fr_oral[0].text))
        for matiere in synoptique.xpath('matières/matière'):
            intitule = matiere.xpath('intitulé')
            if intitule != []:
                intitule = intitule[0].text
            else:
                intitule = 'matière inconnue'
            note = matiere.xpath('note')
            if note != []:
                res.extend('La note en {0:s} {1:s}'.format(intitule, pb) for pb in verifie_flottant(note[0].text))
            rang= matiere.xpath('rang')
            effectif = matiere.xpath('effectif')
            if rang != [] and effectif != []:
                # un max de 1000 semble raisonnable, non?
                pbs = verifie_entier(effectif[0].text, mini=1, maxi=1000)
                pbs.extend(verifie_entier(rang[0].text, mini=1, maxi=pbs != [] and int(effectif[0].text) or 1000))
                res.extend("Le rang ou l'effectif en {0:s} {1:s}".format(intitule, pb) for pb in pbs)
    bulletins = candidat.xpath('bulletins')
    if bulletins != []:
        for bulletin in bulletins:
            matieres = bulletin.xpath('matières')
            if matieres == []:
                continue
            annee = bulletin.xpath('année')
            annee = annee != [] and annee[0].text or 'année inconnue'
            for matiere in matieres:
                intitule = matiere.xpath('intitulé')
                intitule = intitule != [] and intitule[0].text or 'matière inconnue'
                periode = matiere.xpath('date')
                periode = date != [] and date[0].text or 'trimestre inconnu'
                a_note, pbs_note = False, []
                a_mini, pbs_mini = False, []
                a_maxi, pbs_maxi = False, []
                note = matiere.xpath('note')
                if note != []:
                    a_note = True
                    pbs_note = verifie_flottant(note[0].text)
                    res.extend("La note en {0:s} en {1:s} au {2:s} {3:s}".format(intitule, annee, periode, pb) for pb in pbs_note)
                mini = matiere.xpath('mini')
                if mini != []:
                    a_mini = True
                    pbs_mini = verifie_flottant(mini[0].text)
                    res.extend("La note la plus basse en {0:s} en {1:s} au {2:s} {3:s}".format(intitule, annee, periode, pb) for pb in pbs_mini)
                maxi = matiere.xpath('maxi')
                if maxi != []:
                    a_maxi = True
                    pbs_maxi = verifie_flottant(maxi[0].text)
                    res.extend('La note la plus haute en {0:s} en {1:s} au {2:s} {3:s}'.format(intitule, annee, periode, pb) for pb in pbs_mini)
                if a_note and pbs_note == []:
                    if a_mini and pbs_mini == []:
                        note = float(note[0].text.replace(',', '.'))
                        mini = float(mini[0].text.replace(',', '.'))
                        if note < mini:
                            res.append('La note en {0:s} en {1:s} au {2:s} est sous la note la plus basse ({3:f} < {4:f})'.format(intitule, annee, periode, note, mini))
                    if a_maxi and pbs_maxi == []:
                        note = float(note[0].text.replace(',', '.'))
                        maxi = float(maxi[0].text.replace(',', '.'))
                        if note > maxi:
                            res.append('La note en {0:s} en {1:s} au {2:s} est au dessus de la note la plus haute ({3:f} > {4:f})'.format(intitule, annee, periode, note, maxi))
    return res

def verifie_champs(objet, obligatoires, dur = False):
    res = []
    for champ in obligatoires:
        if objet.xpath(champ) == []:
            res.append('{0:s} manquant'.format(champ))
    return res

def verifie_etablissement(etablissement, dur = False):
    res = []
    res.extend("{0:s} dans l'établissement".format(pb) for pb in verifie_champs(etablissement, ['nom', 'ville', 'pays'], dur))
    if 'pays' in etablissement and etablissement['pays'] == 'France' and 'département' not in etablissement:
        res.append('établissement en France sans département')

    return res

def verifie_matiere(matiere, dur = False):
    intitule = matiere.xpath('intitulé')
    # si pas d'intitulé : c'est trop grave
    if intitule == []:
        return ['matière sans intitulé']

    intitule = intitule[0].text

    # si pas matière majeure : ok
    if intitule not in ['Mathématiques', 'Physique/Chimie']:
        return []
    
    res = []
    res.extend('{0:s} en {1:s}'.format(pb, intitule) for pb in verifie_champs(matiere, ['note'], dur))
    
    if res == []:
        intitule = matiere.xpath('intitulé')[0].text
    return res

def verifie_synoptique(synoptique, dur = False):
    res = []
    for champ in ['avis', 'français.écrit', 'français.oral']:
        if synoptique.xpath(champ) == []:
            res.append('Fiche synoptique: {0:s} manquant'.format (champ))
    etablissement = synoptique.xpath('établissement')
    if etablissement != []:
        res.extend('Fiche synoptique: {0:s}'.format(pb) for pb in verifie_etablissement(etablissement[0], dur))
    else:
        res.append('Fiche synoptique: établissement manquant')
    matieres = synoptique.xpath('matières/matière')
    if matieres != []:
        vues = set()
        for matiere in matieres:
            res.extend(['Fiche synoptique: {0:s}'.format(pb) for pb in verifie_matiere(matiere)])
            intitule = matiere.xpath('intitulé')
            if intitule != []:
                vues.add(intitule[0].text)
        absentes = set(['Mathématiques', 'Physique/Chimie']) - vues
        if absentes:
            res.append('Fiche synoptique: matière(s) principale(s) manquantes: {0:s}'.format(', '.join(absentes)))
    else:
        res.append('Fiche synoptique: aucune matière')
    return res

def verifie_notes_dates(matieres, importantes, dates, dur = False):
    res = []
    combinaisons = set((importante, date) for importante in importantes for date in dates)
    for matiere in matieres.xpath('matière'):
        intitule = matiere.xpath('intitulé')
        date = matiere.xpath('date')
        note = matiere.xpath('note')
        if intitule != [] and date != [] and note != []:
            combinaisons.discard((intitule[0].text, date[0].text))
    for intitule, date in combinaisons:
        res.append('pas de note en {0:s} au {1:s}'.format(intitule, date))
    return res

def de_sainte(bulletin):
    codes = bulletin.xpath('établissement/code')
    if codes == []:
        return False
    else:
        return codes[0] == '071157R'

def verifie_bulletin(bulletin, dur = False):
    res = []
    annee = bulletin.xpath('année')
    if annee == []:
        res.append('bulletin sans année')
        return res
    annee = annee[0].text

    # si ce n'est pas une année qui nous intéresse, on ne regarde pas
    if annee not in [annee_premiere, annee_terminale]:
        return res
    matieres = bulletin.xpath('matières/matiere')
    if matieres != []:
        if annee == annee_premiere:
            res.extend('{0:s} en première'.format(pb) for pb in verifie_notes_dates(matieres[0], ['Mathématiques', 'Physique/Chimie'], ['trimestre 1', 'trimestre 2'], dur))
            # Ne pas exiger de note au troisième trimestre pour les
            # élèves de Sainte, reconnu à son code établissement
            if not de_sainte(bulletin):
                res.extend('{0:s} en première'.format(pb) for pb in verifie_notes_dates(matieres[0], ['Mathématiques', 'Physique/Chimie'], ['trimestre 3'], dur))
        if annee == annee_terminale:
            res.extend('{0:s} en terminale'.format(pb) for pb in verifie_notes_dates(matieres[0], ['Mathématiques', 'Physique/Chimie'], ['trimestre 1', 'trimestre 2'], dur))
    for matiere in bulletin.xpath('matières/matière[not(note)]'):
            if dur:
                res.append('pas de note en {0:s} en {1:s}'.format(matiere['intitulé'], 'année' in bulletin and bulletin['année'] or 'année inconnue'))
    return res

def verifie_candidat(candidat, dur = False):
    res = []
    res.extend(verifie_valeurs_numeriques(candidat, dur))
    for champ in ['nom', 'prénom', 'naissance', 'id_apb']:
        if candidat.xpath(champ) == []:
            res.append('Candidat sans {0:s}'.format(champ))
    if candidat.xpath('sexe') == [] and dur:
        res.extend('Candidat sans sexe')
    if candidat.xpath('sexe') != [] and candidat.xpath('sexe')[0].text not in 'FM' and dur:
        res.extend("Candidat d'un autre sexe: {0:s}".format(candidat.xpath('sexe')[0].text))
    if candidat.xpath('synoptique') != []:
        res.extend(verifie_synoptique(candidat.xpath('synoptique')[0], dur))
    else:
        res.append('Absence de fiche synoptique')
    bulletins = candidat.xpath('bulletins/bulletin')
    if bulletins != []:
        for bulletin in bulletins:
            res.extend(verifie_bulletin(bulletin, dur))
    else:
        res.append('Aucun bulletin')
    return res

def genere_liste_questions(candidats, dur = False):
    questions_par_candidat = []
    for candidat in candidats.xpath('candidat'):
        pbs = verifie_candidat(candidat, dur)
        if pbs != []:
            questions_par_candidat.append((candidat, pbs))
    # Un beau dictionnaire, dont les clefs sont les codes des
    # établissements (à défaut leur nom, à défaut un juron) et les
    # valeurs un triplet dont le premier élément est le numéro de
    # téléphone si on l'a, le second élément le nom de l'établissement
    # si on l'a et le troisième et dernier la liste des paires
    # (candidat, problèmes).
    questions_par_etablissement = dict()
    for candidat, pbs in questions_par_candidat:
        clef = None
        nom = None
        telephone = None
        synoptique = candidat.xpath('synoptique')
        if synoptique != []:
            synoptique = synoptique[0]
            etablissement = synoptique.xpath('établissement')
            if etablissement != []:
                etablissement = etablissement[0]
                clef = etablissement.xpath('code')
                if clef != []:
                    clef = clef[0].text
                else:
                    clef = None
                nom = etablissement.xpath('nom')
                if nom != []:
                    nom = nom[0].text
                    if not clef:
                        clef = nom
                telephone = etablissement.xpath('téléphone')
                if telephone != []:
                    telephone = telephone[0].text
        if not clef:
            clef = 'un juron' # promesse tenue!
        if clef in questions_par_etablissement:
            tele, autre_nom, lst = questions_par_etablissement[clef]
            lst.append((candidat, pbs))
            questions_par_etablissement[clef] = (tele or telephone, autre_nom or nom, lst)
        else:
            questions_par_etablissement[clef] = (telephone, nom, [(candidat, pbs)])
    for clef, (telephone, nom, lst) in questions_par_etablissement.items():
        print('Appeler {0:s} au {1:s} pour:'.format(nom or 'on-ne-sait-qui', telephone or 'on-ne-sait-où'))
        for candidat, pbs in lst:
            if candidat.xpath('nom') != []:
                if candidat.xpath('prénom') != []:
                    nom = ' '.join([candidat.xpath('prénom')[0].text,candidat.xpath('nom')[0].text])
                else:
                    nom = candidat.xpath('nom')[0].text
            else:
                nom = 'anonyme'
            if candidat.xpath('id_apb') != []:
                id_apb = candidat.xpath('id_apb')[0].text
            else:
                id_apb = 'sans'
            if candidat.xpath('INE') != []:
                ine = candidat.xpath('INE')[0].text
            else:
                ine = 'sans'
            print('\t{0:s} (numéro: {1:s}, INE: {2:s})'.format(nom, id_apb, ine))
            for pb in pbs:
                print('\t\t{0:s}'.format(pb))
