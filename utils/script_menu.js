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

function tableaux_wait()
{
    show_loader();
    var form = document.getElementById('tableaux');
    setTimeout(function() {form.submit();},200);
}
