// Mettre en place un gestionnaire d'évènements lié à la function python refresh
if (!!window.EventSource) {
	var refresh = new EventSource('/refresh');
}

// Ajouter un écouteur d'évènements qui recharge la page sur un event 'add'
refresh.addEventListener('add', function(event) {
		window.location.reload(true);
}, false);

// Ajouter un écouteur d'évènements qui recharge la page sur un event 'free'
refresh.addEventListener('free', function(event) {
		window.location.reload(true);
}, false);

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
    list = document.getElementsByClassName("fichier");
	if (list.length > 1)
	{
		var rep = confirm('Attention, cette action entraînera la réinitialisation de tous les fichiers	ADMIN.\n Toutes les modifications apportées seront perdues.\n Cliquez sur OK pour continuer.');
	}
	if (rep || list.length <= 1)
	{
		// Soumission du formulaire
		document.getElementById('traiter').submit()
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
