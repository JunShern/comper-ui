
var p5sketch = function( p ) {
    var keys = [];
    var channel_colours = _.range(16).map(i => 'hsl('+Math.round((i+7)%16*360/16)+',100%,50%)');
    var NUM_KEYS = 128;
    var NOTE_ON = 144;
    var NOTE_OFF = 128;
    var midiAccess;
    var synth;
    var recordStatusColor = [0, 0, 20];
    var audioContext;
    var cycleStartACtime;
    var ticksPerBeat = 24, beatsPerUnit = 4;
    var secsPerTick;
    var inputEventsList = createArray(128, 0);
    var loopStatus = 0;

    function Key(index, key_w, key_h) {
        this.index = index;
        this.width = key_w - 4;
        this.height = key_h;
        this.left_edge = index * key_w;
        this.type = NOTE_OFF;
        this.channel = 0;
        this.velocity = 0;
        this.colour_off = p.color(0,0,10);
        this.colour_on = _.range(16).map(i => p.color(Math.round((i+7)%16*360/16),100,100,1) );

        this.draw = function() {
            // Always draw the empty key first, assuming note is off
            p.fill(this.colour_off);
            p.rect(this.left_edge, p.height-this.height, this.width, this.height);
            // Draw coloured key based on velocity (will end up transparent for NOTE_OFF since velocity=0)
            this.colour_on[this.channel]._array[3] = this.velocity;
            // console.log(this.colour_on[this.channel]);
            p.fill(this.colour_on[this.channel]);
            p.rect(this.left_edge, p.height-this.height, this.width, this.height);
        }
    }
    
    p.preload = function() {
        p.soundFormats('wav');
        hihat = p.loadSound('hihat');
    }

    p.setup = function() {
        p.createCanvas(p.windowWidth, p.windowHeight/2);
        p.noStroke();
        p.frameRate(12);
        p.colorMode(p.HSB); // Max values: 360, 100, 100, 1
        p.textFont('monospace');

        // request MIDI access
        if (navigator.requestMIDIAccess) {
            navigator.requestMIDIAccess({
                sysex: false
            }).then(onMIDISuccess, onMIDIFailure);
        } else {
            alert("No MIDI support in your browser.");
        }

        // Synth
        // synth = new p5.MonoSynth();
        synth = new Tone.PolySynth().toMaster();


        var keys_width = p.width / NUM_KEYS;
        var keys_height = 50;
        for (var i=0; i<NUM_KEYS; i++) {
            key = new Key(i, keys_width, keys_height)
            keys.push(key);
        }

        // Create SoundLoop with 8th-note-long loop interval
        audioContext = p.getAudioContext(); // For timing and recording
        sloop = new p5.SoundLoop(soundLoop, "1n");
        sloop.bpm = 60; // 80 beats per minute
    }

    function soundLoop(cycleStartTime) {
        cycleStartACtime = audioContext.currentTime;
        // Play sound
        beatSeconds = this._convertNotation('4n');
        hihat.playMode('restart');
        hihat.play(cycleStartTime + 0*beatSeconds);
        hihat.play(cycleStartTime + 1*beatSeconds);
        hihat.play(cycleStartTime + 2*beatSeconds);
        hihat.play(cycleStartTime + 3*beatSeconds);
        var secsPerUnit = this._convertNotation(this._interval);
        secsPerTick = secsPerUnit / (ticksPerBeat * beatsPerUnit);

        compMode = $("input[name=comp_mode]:checked").val();
        if (loopStatus == 1) {
            compEventsList = inputEventsList.slice() // Make a copy
            for (var tick=0; tick<compEventsList.length; tick++) {
                for (var msg_ind=0; msg_ind<compEventsList[tick].length; msg_ind++) {
                    var msg = compEventsList[tick][msg_ind];
                    msg.channel = 6;
                    var startTime = tick*secsPerTick;
                    setTimeout(displayNewMessage, startTime*1000, msg);
                    if (msg.type === NOTE_ON) {
                        synth.triggerAttack(p.midiToFreq(msg.note), cycleStartACtime + startTime, msg.velocity);
                    } else if (msg.type === NOTE_OFF) {
                        synth.triggerRelease(p.midiToFreq(msg.note), cycleStartACtime + startTime);
                    }
                }
            }
            recordStatusColor = [0, 0, 20];
        } else if (loopStatus == 0) {
            inputEventsList = createArray(128, 0); // Reset the input
            recordStatusColor = [0, 70, 80];
        }

        loopStatus = 1 - loopStatus;

        // // Add a particle to visualize the note
        // var pitchClassIndex = pentatonic_scale.indexOf(pitchClass);
        // var xpos = width / (pentatonic_scale.length * 2) + pitchClassIndex * width / pentatonic_scale.length;
        // var ypos = height - heightLevel * height / numOctaves;
        // system.addParticle(xpos, ypos);
    }

    p.mouseClicked = function() {
        if (sloop.isPlaying) {
            sloop.pause();
        } else {
            sloop.start();
        }
    }

    p.draw = function() { 
        p.background(0);
        for (var i=0; i<NUM_KEYS; i++) {
            keys[i].draw();
        }
        p.fill(255);
        // Play/pause controls
        p.textAlign(p.LEFT, p.BOTTOM);
        if (sloop.isPlaying) p.text('Click to Pause', 10, p.height - 60);
        else p.text('Click to Play', 10, p.height - 60);
        // Display loop status
        p.fill(recordStatusColor);
        p.stroke(50);
        p.strokeWeight(3);
        p.ellipse(p.width/2, p.height/2, 50, 50);
        p.noStroke();
    }

    function onMIDISuccess(midiAccess_) {
        midiAccess = midiAccess_
        var inputs = midiAccess.inputs.values();
        for (var input = inputs.next(); input && !input.done; input = inputs.next()) {
            // Create a checkbox for each available port
            var container = document.getElementById('checkbox_container');

            var div = document.createElement('div');
            var checkbox = document.createElement('input');
            checkbox.type = "checkbox";
            checkbox.name = "midi_input_checkbox";
            checkbox.value = input.value.name;
            checkbox.id = input.value.name;
            checkbox.addEventListener("change", function() {
                var inputs = midiAccess.inputs.values();
                for (var input = inputs.next(); input && !input.done; input = inputs.next()) {
                    // Assign callback function to the selected MIDI input(s)
                    cb = document.getElementById(input.value.name);
                    if (cb.checked) { 
                        input.value.onmidimessage = onMIDIMessage;
                    } else {
                        input.value.onmidimessage = null;
                    }
                }
            });

            var label = document.createElement('label')
            label.htmlFor = input.value.name;
            label.appendChild(document.createTextNode(input.value.name));

            div.appendChild(checkbox);
            div.appendChild(label);
            container.appendChild(div);
        }
    }
    function onMIDIFailure(e) {
        // when we get a failed response, run this code
        console.log("No access to MIDI devices or your browser doesn't support WebMIDI API. Please use WebMIDIAPIShim " + e);
    }

    function MIDI_Message(data) {
        /*
        data is Uint8Array[3] with
        data[0] : command/channel
        data[1] : note
        data[2] : velocity
        */
        this.cmd = data[0] >> 4;
        this.channel = data[0] & 0xf; // 0-15
        this.type = data[0] & 0xf0;
        this.note = data[1];
        this.velocity = data[2];
        if (this.velocity == 0) {
            this.type = NOTE_OFF;
        }

        this.toString = function() {
            return 'type=' + this.type + 
                ' channel=' + this.channel + 
                ' note=' + this.note + 
                ' velocity=' + this.velocity;
        }
    }

    function write_to_console(text, color) {
        container = document.getElementById("console");
        // Create new paragraph element with text
        paragraph = document.createElement("p");
        var textnode = document.createTextNode(text);
        paragraph.appendChild(textnode);
        paragraph.className = "consoletext";
        paragraph.style.color = color;
        container.appendChild(paragraph);
        // Delete nodes if too many children
        if (document.getElementById('console').children.length > 200) {
            var firstchild = document.getElementById('console').children[0];
            document.getElementById('console').removeChild(firstchild);    
        }
        // Scroll to bottom of console container
        console_container = document.getElementById("console_container");
        console_container.scrollTop = console_container.scrollHeight;
    }

    function displayNewMessage(msg) {
        keys[msg.note].type = msg.type;
        keys[msg.note].channel = msg.channel;
        keys[msg.note].velocity = msg.velocity;
        write_to_console(msg.toString(), channel_colours[msg.channel]);
    }

    function onMIDIMessage(data) {
        msg = new MIDI_Message(data.data);
        msg.velocity = Math.round(msg.velocity / 127 * 100) / 100;
        displayNewMessage(msg);
        // keys[msg.note].type = msg.type;
        // keys[msg.note].channel = msg.channel;
        // keys[msg.note].velocity = msg.velocity;
        // write_to_console(msg.toString(), channel_colours[msg.channel]);
        if (msg.type === NOTE_ON) {
            synth.triggerAttack(p.midiToFreq(msg.note), undefined, msg.velocity);
        } else if (msg.type === NOTE_OFF) {
            synth.triggerRelease(p.midiToFreq(msg.note));
        }

        // Register in input events list if loop has started
        if (cycleStartACtime) {
            timeFromUnitStart = audioContext.currentTime - cycleStartACtime;
            tick = Math.floor(timeFromUnitStart / secsPerTick);   
            inputEventsList[tick].push(msg);
        }
    }
};

function createArray(length) {
    var arr = new Array(length || 0),
        i = length;

    if (arguments.length > 1) {
        var args = Array.prototype.slice.call(arguments, 1);
        while(i--) arr[length-1 - i] = createArray.apply(this, args);
    }

    return arr;
}