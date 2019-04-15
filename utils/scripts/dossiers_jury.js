function toFloat(str)
{
    // fonction de conversion
    return parseFloat(str.replace(",", "."));
}

function maj_note()
{
    // mise à jour du score final (en live)
	var correc = document.getElementById('correc');
	var cor = toFloat(correc.value);
	var min = toFloat(correc.min);
    if (cor == min) // Clic sur NC
    {
    	document.getElementById('scoref').innerHTML = 'NC';
    } else {
    	var scorb = toFloat(document.getElementById('scoreb').innerHTML);
		var scorf = (scorb + cor).toFixed(2).replace('.',',');
    	document.getElementById('scoref').innerHTML = scorf;
    }
}

function maj_motif(id)
{
    // lancée par les boutons (+) relatifs aux motivations du jury
    // le paramètre name est le nom du bouton et du label associé !
    // On va mettre à jour la zone de texte motif...
	var src = document.getElementById(id);
	var dest = document.getElementById('motif');
	if (dest.value != '')
	{dest.value += ' | '}
	dest.value += src.value;
}

function click_range()
{
    maj_note();
}

function test_valid()
{
    // lancée à la validation du formulaire, cette fonction
    // renvoie true pour soumettre le formulaire si tout va bien
    // et false sinon...
    // Mémorise le scroll de liste
    get_scroll();
	// vérifie qu'il y a un motif si correc <> 0 ou NC
	// Récupération de la correction
	var correc = document.getElementById('correc');
	var cor = toFloat(correc.value);
	// Si elle est non nulle ou NC, on teste l'existence d'une motivation
	var motif = document.getElementById('motif');
	var test = false; // test sera vrai si au moins une motivation est saisie ou si correction = 0
	var txt = 'Toute correction apportée au score doit être motivée...';
	if (motif.value.substring(0,9)=='- Admin :')
	{
		if (cor == 0){txt = "La remarque de l'Administrateur doit être supprimée...";}
	}
	else if (motif.value == '')
	{
		if (cor == 0){test = true;}
	}
	else
	{
		test = true
	}
	// --> message et formulaire non soumis
	if (!test)
	{alert(txt);}
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
