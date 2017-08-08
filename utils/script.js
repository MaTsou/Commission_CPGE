function toFloat(str)
{
    // fonction de conversion
    return parseFloat(str.replace(",", "."));
}

function maj_note()
{
    // mise à jour du score final (en live)
    var nc = document.getElementById('nc');
    if (nc.value == 'NC')
    {
    	document.getElementById('scoref').innerHTML = 'NC';
    } else {
    	var correc = document.getElementById('correc');
    	cor = toFloat(correc.value);
    	var scorb = toFloat(document.getElementById('scoreb').innerHTML);
	var scorf = (scorb + cor).toFixed(2).replace('.',',');
    	document.getElementById('scoref').innerHTML = scorf;
    }
}

function click_nc()
{
    // Admin ou Jury ?
    txt = document.getElementById("header").innerHTML
    if (txt.indexOf('Admin') == -1){
		// Accès Jury
	    // mise à jour du input hidden nc et soumission formulaire
	    nc = document.getElementById('nc');
	    nc.value = 'NC';
	    maj_note();
	    valid = test_valid();
	    if (valid) {document.forms['formulaire'].submit();}
    }
}

function maj_motif(id)
{
    // lancée par les boutons (+) relatifs aux motivations du jury
    // le paramètre name est le nom du bouton et du label associé !
    // On va mettre à jour la zone de texte motif...
    // Admin ou Jury ?
    txt = document.getElementById("header").innerHTML
    if (txt.indexOf('Admin') == -1){
    	    // Accès Jury
            src = document.getElementById(id);
            dest = document.getElementById('motif');
            if (dest.value != '')
            {dest.value += ' | '}
            dest.value += src.value;
    }
}

function click_range()
{
    // permet de sortir d'un cas NC par clic sur les notes
    nc = document.getElementById('nc');
    nc.value = '';
    maj_note();
}

function verif_saisie()
{
	// Cette fonction vérifie la saisie des notes par l'Administrateur
	// Si elles ne sont pas numériques ou hors de [0;20], un message apparaît...
	val = event.target.value;
	if (val != parseFloat(val) && val != '-'){
		alert("Une valeur numérique (ou '-') est attendue...");
		event.target.focus()
	}
	if (val == parseFloat(val) && (parseFloat(val) <0 || parseFloat(val) >20)){
		alert("La valeur saisie n'est pas comprise entre 0 et 20");
		event.target.focus()
	}
}

function test_valid()
{
    // lancée à la validation du formulaire, cette fonction
    // renvoie true pour soumettre le formulaire si tout va bien
    // et false sinon...
    // Mémorise le scroll de liste
    get_scroll();
    // Admin ou Jury ?
    txt = document.getElementById("header").innerHTML;
    if (txt.indexOf('Admin') == -1){
    	// Accès Jury
    	// vérifie qu'il y a un motif si correc < 0 ou NC
        // Récupération de la correction
        correc = document.getElementById('correc');
        cor = toFloat(correc.value);
        nc = document.getElementById('nc');
        // Si elle est négative ou NC, on teste l'existence d'une motivation
        motif = document.getElementById('motif');
        test = false; // test est vrai si au moins une motivation est saisie
        if (cor >= 0 && nc.value!=='NC'){test = true;}
        if (motif.value != ''){test = true;}
        // --> message et formulaire non soumis
        if (!test)
        {alert('Les corrections négatives (et aussi NC !) doivent obligatoirement être motivées...');}
    }
    else {
    	// Accès Admin
	test = True;
    }
    return test
}

function get_scroll()
{
    // lancée lors de l'usage de l'ascenseur sur la liste
    // sert à mémoriser la position de l'ascenseur
    // pour y revenir à l'actualisation de la page...
    // récupération de la valeur du scroll
    var div = document.getElementById('liste');
    var scro = div.scrollTop;//getElementById('liste').scrollTop;
    // stockage dans le champ caché... (en haut de la liste) id = scroll_mem
    var stock = document.getElementsByName('scroll_mem')[0];
    stock.value = scro;
}

function set_scroll()
{
    // lancée au chargement de la liste
    // sert à retrouver la position de la scroll-bar et arrête le please wait
    var stock = document.getElementsByName('scroll_mem')[0];
    // définir le scroll à cette valeur
    var div = document.getElementById('liste');
    div.scrollTop = stock.value;
}
