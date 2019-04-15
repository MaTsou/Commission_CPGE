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
    } else
	{
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
    // Admin : rien ne se passe
	{}
}

function click_range()
{
	// Mise à jour de la note
	maj_note();
}

function verif_saisie()
{
	// Cette fonction vérifie la saisie des notes par l'Administrateur
	// Si elles ne sont pas numériques ou hors de [0;20], un message apparaît...
	var val = event.target.value;
	var ok = true;
	if (isNaN(toFloat(val)) && val != '-')
	{
		alert("Une valeur numérique (ou '-') est attendue...");
		event.target.focus();
		event.target.value = '-';
		ok = false;
	}
	if (!isNaN(toFloat(val)) && (toFloat(val) <0 || toFloat(val) >20))
	{
		alert("La valeur saisie n'est pas comprise entre 0 et 20");
		event.target.focus();
		event.target.value = '-';
		ok = false;
	}
	return ok
}

function test_valid()
{
    // lancée à la validation du formulaire, cette fonction
    // renvoie true pour soumettre le formulaire si tout va bien
    // et false sinon...
    // Mémorise le scroll de liste
    get_scroll();
	// Récupération de la correction
	var correc = document.getElementById('correc');
	var cor = toFloat(correc.value);
	var min = toFloat(correc.min);
	// Récupération du motif
	var motif = document.getElementById('motif');
	// test
	if (cor == min && motif.value == '') // NC non motivé ??
	{
		alert('Veuillez renseigner le champ motivation');
		return false
	}
    return true
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
