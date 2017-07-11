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
    // mise à jour du input hidden nc et soumission formulaire
    nc = document.getElementById('nc');
    nc.value = 'NC';
    maj_note();
    valid = test_valid();
    if (valid) {document.forms['formulaire'].submit();}
}

function maj_motif(id)
{
    // lancée par les boutons (+) relatifs aux motivations du jury
    // le paramètre name est le nom du bouton et du label associé !
    // On va mettre à jour la zone de texte motif...
    //elem = document.getElementById(id)
    src = document.getElementById(id);
    dest = document.getElementById('motif');
    if (dest.value != '')
    {dest.value += ' | '}
    dest.value += src.value;
    return None
}

function click_range()
{
    // permet de sortir d'un cas NC par click sur le range
    nc = document.getElementById('nc');
    nc.value = '';
    maj_note();
}

function test_valid()
{
    // lancée à la validation du formulaire
    // cette fonction vérifie qu'il y a un motif si correc < 0 ou NC
    // renvoie true pour 'submit' le formulaire (tout ok) et false sinon...
    // Mémorise le scroll de liste
    get_scroll()
    // Récupération de la correction
    correc = document.getElementById('correc');
    cor = toFloat(correc.value);
    nc = document.getElementById('nc');
    // Si elle est négative ou NC, on test l'existence d'une motivation
    motif = document.getElementById('motif');
    test = false; // test est vrai si au moins une motivation est saisie.
    if (cor >= 0 && nc.value!=='NC'){test = true;}
    if (motif.value != ''){test = true;}
    // --> message et formulaire non soumis
    if (!test)
    {alert('Les corrections négatives (et aussi NC !) doivent obligatoirement être motivées...');}
    return test
}

function get_scroll()
{
    // lancée lors de l'usage de l'ascenseur sur la liste.
    // sert à mémoriser la position de l'ascenceur
    // pour y revenir à l'actualisation de la page...
    // récupération valeur du scroll
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
    // récupération de la valeur (passée en argument : 'mem_scroll'
    var stock = document.getElementsByName('scroll_mem')[0];
    // définir le scroll à cette valeur
    var div = document.getElementById('liste');
    div.scrollTop = stock.value;
}

function hide_loader()
{
    document.getElementById("patience").style.visibility = "hidden";
}

function show_loader()
{
    document.getElementById('patience').style.visibility = 'visible';
}

function verif_wait()
{
    list = document.getElementsByClassName('fichier');
    var rep = true;
    if (list.length > 3){
	rep = confirm('Attention, cette action entraînera la réinitialisation de tous les fichiers ADMIN.\n Toutes les modifications apportées seront perdues.\n Cliquez sur OK pour continuer.');
    };
    if (rep) {
	show_loader();
	var form = document.getElementById('traiter');
	setTimeout(function() {form.submit();},200);
    }
}

function genere_wait()
{
    show_loader();
    var form = document.getElementById('genere');
    setTimeout(function() {form.submit();},200);
}

function recolt_wait()
{
    show_loader();
    var form = document.getElementById('recolte');
    setTimeout(function() {form.submit();},200);
}

function impress_wait()
{
    show_loader();
    var form = document.getElementById('impress');
    setTimeout(function() {form.submit();},200);
}

function tableaux_wait()
{
    show_loader();
    var form = document.getElementById('tableaux');
    setTimeout(function() {form.submit();},200);
}
