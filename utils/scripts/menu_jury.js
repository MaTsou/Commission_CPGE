// Mettre en place un gestionnaire d'évènements lié à la function python refresh
if (!!window.EventSource) {
	var refresh = new EventSource('/refresh');
}

// Affecter une fonction à exécuter à la réception d'un event 'add'
refresh.addEventListener('add',
	function(event) {
		if (event.data !== '') {
			document.getElementById(event.data).disabled = true;
		}
	},
	false);

// Affecter une fonction à exécuter à la réception d'un event 'free'
refresh.addEventListener('free',
	function(event) {
		if (event.data !== '') {
			document.getElementById(event.data).disabled = false;
		}
	},
	false);
