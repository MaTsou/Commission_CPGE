// Mettre en place un gestionnaire d'évènements lié à la function python refresh
if (!!window.EventSource) {
	var refresh = new EventSource('/refresh');
}

// Ajouter un écouteur d'évènements qui recharge la page
refresh.addEventListener('message', function(event) {
		window.location.reload(true);
});

function hide_loader() // Admin seulement
{}

function show_loader() // Admin seulement
{}

function verif_wait() // Admin seulement
{}

function genere_wait() // Admin seulement
{}

function recolt_wait() // Admin seulement
{}

function tableaux_wait() // Admin seulement
{}
