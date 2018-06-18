// setup some JSON to use
var pianorollInput = [
	{ "make":"Porsche", "model":"911S" },
	{ "make":"Mercedes-Benz", "model":"220SE" },
	{ "make":"Jaguar","model": "Mark VII" }
];

window.onload = function() {
}

function getPianoroll() {
	// ajax the JSON to the server
	$.post("receiver", JSON.stringify(pianorollInput), function(resp){
		json_obj = JSON.parse(resp);
		myp5.drawPianoroll(json_obj);
	});
}
