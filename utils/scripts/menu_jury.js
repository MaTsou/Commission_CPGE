// Mettre en place un gestionnaire d'évènements lié à la function python send_sse_message
//if (!!window.EventSource) {
//	var source = new EventSource('/send_sse_message');
//}
//
//// Affecter une fonction à exécuter à la réception d'un event 'add'
//source.addEventListener('add',
//	function(event) {
//		if (event.data !== '') {
//			document.getElementById(event.data).disabled = true;
//		}
//	},
//	false);
//
//// Affecter une fonction à exécuter à la réception d'un event 'free'
//source.addEventListener('free',
//	function(event) {
//		if (event.data !== '') {
//			document.getElementById(event.data).disabled = false;
//		}
//	},
//	false);
