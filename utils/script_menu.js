// Mettre en place un gestionnaire d'évènements lié à la function python refresh
if (!!window.EventSource) {
	var refresh = new EventSource('/refresh');
}

// Ajouter un écouteur d'évènements qui recharge la page
refresh.addEventListener('message', function(event) {
		window.location.reload(true);
});

function hide_loader()
{
	var txt = document.getElementById("header").innerHTML
	if (txt.indexOf('Admin') != -1){
		// Accès Admin
		document.getElementById("patience").style.visibility = "hidden";
	}
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
		// Ici, une boite prompt pour confirmer la valeur de la variable annee_en_cours
		annee = document.getElementById("annee").value;
		annee = prompt("Veuillez confirmer ou saisir l'année courante :",annee);
		if (annee != null) {
			document.getElementById("annee").value = annee;
			// Veuillez patientez puis soumission formulaire..
			show_loader();
			var form = document.getElementById('traiter');
			setTimeout(function() {form.submit();},200);}
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
