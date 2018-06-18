var keys = [];
// var channel_colours = _.range(16).map(i => 'hsl('+Math.round((i+7)%16*360/16)+',100%,50%)');

var p5sketch = function( p ) {
    var NUM_KEYS = 128;
    var NOTE_ON = 144;
    var NOTE_OFF = 128;
    // var NUM_PITCHES = 128;
    // var NUM_TICKS = 96;

    var sloop;
    var synth;

    var input_pianoroll;
    var comp_pianoroll;

    p.setup = function() {
        p.createCanvas(p.windowWidth, p.windowHeight);
        p.background(0);

        // Sound
        synth = new p5.PolySynth();
        // sloop = new p5.SoundLoop(soundLoop, "1m");
        // sloop.bpm = 80;
        // sloop.start();
        
        setInterval(serverUpdate, 1000); // Sync against server every second
    }

    // function soundLoop(cycleStartTime) {
    //     synth.play('C4', 0.8, cycleStartTime, 1);
    //     synth.play('C4', 0.8, cycleStartTime + sloop._convertNotation("4n"), 1);
    //     synth.play('C4', 0.8, cycleStartTime + 2*sloop._convertNotation("4n"), 1);
    //     synth.play('C4', 0.8, cycleStartTime + 3*sloop._convertNotation("4n"), 1);
    // }
      

    function serverUpdate() {
        // ajax the JSON to the server
        $.post("input_endpoint", JSON.stringify(pianorollInput), function(resp){
            input_pianoroll = JSON.parse(resp);
        });
        $.post("comp_endpoint", JSON.stringify(pianorollInput), function(resp){
            comp_pianoroll = JSON.parse(resp);
        });        
    }

    p.draw = function() {
        p.background(0);
        if (input_pianoroll) {
            p.drawPianoroll(input_pianoroll);
        }
        if (comp_pianoroll) {
            p.drawPianoroll(comp_pianoroll);
        }
    }

    p.drawPianoroll = function(pianoroll) {
        NUM_PITCHES = pianoroll.length;
        NUM_TICKS = pianoroll[0].length;
        pianoroll_width = p.width/3;
        pianoroll_height = p.height;
        var grid_w = pianoroll_width / NUM_TICKS;
        var grid_h = pianoroll_height / NUM_PITCHES;

        p.noStroke();
        for (var pitch=0; pitch<NUM_PITCHES; pitch++) {
            for (var tick=0; tick<NUM_TICKS; tick++) {
                if (pianoroll[pitch][tick] !== 0) {
                    p.fill(255, 0, 0, pianoroll[pitch][tick] * 255);
                    p.rect(tick*grid_w, pianoroll_height - pitch*grid_h, grid_w, grid_h);    
                }
            }
        }
    }

};
