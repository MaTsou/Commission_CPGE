#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import PyPDF2,os
from parse import parse
from parse import compile


def decoup(sourc, dest): # source = fichier -- dest = dossier
	regex = compile('{}Dossier n°{id:d}{}Page {page:d}') # compilation de la requête
													# pour gagner du temps !
	pdfFileObj = open(sourc, 'rb')
	pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
	page_deb = -1
	id_cand = -1
	pdfWriter = PyPDF2.PdfFileWriter() # pour le candidat -1 (plutôt qu'un test)
	
	for page in range(0,pdfReader.numPages):
		pageObj = pdfReader.getPage(page)		# on récupère la page courante
		txt = pageObj.extractText()				# on récupère le texte de la page
		res = regex.parse(txt)					# récupération n° dossier et Page
		if res or page == pdfReader.numPages-1:
			if id_cand != res['id'] or page == pdfReader.numPages-1:	# changement de candidat? fin ?
				nom = dest+'/docs_{}.pdf'.format(id_cand)
				pdfOutputFile = open(nom, 'wb')
				if page == pdfReader.numPages-1: pdfWriter.addPage(pageObj) # sinon il en manque un bout..
				pdfWriter.write(pdfOutputFile) # Super, ça écrase tout fichier existant !!
				pdfOutputFile.close()
				# réinitialisations
				pdfWriter = PyPDF2.PdfFileWriter()
				id_cand = res['id']
			pdfWriter.addPage(pageObj)
	os.remove(dest+'/docs_-1.pdf')	