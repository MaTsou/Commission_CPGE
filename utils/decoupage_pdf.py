#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import PyPDF2,os
from parse import parse
from parse import compile


def decoup(sourc, dest):
	"sourc: fichier source"
	"dest: dossier destination"
	# précompilation de la requête pour gagner en vitesse
	regex = compile('{}Dossier n°{id:d}{}Page {page:d}')
	pdfFileObj = open(sourc, 'rb')
	pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
	page_deb = -1
	id_cand = -1
        # pour le candidat -1, au lieu de faire un cas particulier
	pdfWriter = PyPDF2.PdfFileWriter()

	for page in range(pdfReader.numPages):
                # récupération de la page courante
		pageObj = pdfReader.getPage(page)
                # puis de son texte brut
		txt = pageObj.extractText()
                # et enfin, numéro de dossier et page
		res = regex.parse(txt)
		if res or page == pdfReader.numPages-1:
                        # est-ce un changement de candidat?
			if (id_cand != res['id']
                            or page == pdfReader.numPages-1):
				nom = os.path.join (dest, 'docs_{}.pdf'.format(id_cand))
				pdfOutputFile = open(nom, 'wb')
                                # sinon il en manque un bout
				if page == pdfReader.numPages-1:
                                        pdfWriter.addPage(pageObj)
                                # écrasement de tout fichier existant!!
				pdfWriter.write(pdfOutputFile)
				pdfOutputFile.close()
				# réinitialisations
				pdfWriter = PyPDF2.PdfFileWriter()
				id_cand = res['id']
			pdfWriter.addPage(pageObj)
	os.remove(os.path.join(dest, 'docs_-1.pdf'))
