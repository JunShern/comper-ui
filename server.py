import sys
import time

from flask import Flask, render_template, request, redirect, Response
import random, json
import numpy as np
import pianoroll_utils
import unit_predictor

NUM_PITCHES = 128
NUM_TICKS = 96
COMP_CHANNEL = 6

app = Flask(__name__)

def np_to_json(np_matrix):
    return json.dumps(np_matrix.tolist())

@app.route('/')
def output():
    # serve index template
    matrix = np_to_json(np.random.rand(2, 3))
    return render_template('index.html', matrix=matrix)

@app.route('/input_endpoint', methods = ['POST'])
def get_input_pianoroll():
    # mat = np.random.rand(NUM_PITCHES, NUM_TICKS)
    mat = np.zeros((NUM_PITCHES, NUM_TICKS))
    mat[60] = 1
    mat[65,:48] = 0.5
    mat[67,48:] = 0.5
    matrix = np_to_json(mat)
    return matrix

@app.route('/comp_endpoint', methods = ['POST'])
def get_comp_pianoroll():
    # Parse data into input pianoroll
    data = request.get_json(force=True)
    input_pianoroll = jsonevents_2_pianoroll(data)
    # Predict comp pianoroll
    comp_pianoroll = unit_predictor.get_comp_pianoroll(input_pianoroll) #input_pianoroll.copy()
    # Format data for JSON
    comp_events = pianoroll_2_jsonevents(comp_pianoroll)
    return json.dumps(comp_events)

def jsonevents_2_pianoroll(events):
    assert(len(events) == NUM_TICKS)
    pianoroll = np.zeros((NUM_PITCHES, NUM_TICKS))
    for tick, tick_events in enumerate(events):
        for msg_event in tick_events:
            pitch = msg_event[u'note']
            velocity = msg_event[u'velocity']
            pianoroll[pitch, tick:] = velocity
    return pianoroll

def pianoroll_2_jsonevents(pianoroll, min_pitch=0, max_pitch=127, is_onsets_matrix=False):
    assert pianoroll.shape[0] == max_pitch - min_pitch + 1
    num_pitches = pianoroll.shape[0]
    num_ticks = pianoroll.shape[1]
    
    assert np.max(pianoroll) <= 1 # Pianorolls must be normalized between 0 and 1
    pianoroll = pianoroll * 127

    events = [[] for _ in range(num_ticks)] # Each tick gets a list to store events
    clipped = pianoroll.astype(int)
    binarized = clipped.astype(bool)
    padded = np.pad(binarized, ((0, 0), (1, 1)), 'constant')
    diff = np.diff(padded.astype(int), axis=1)

    for p in range(num_pitches):
        pitch = min_pitch + p
        note_ons = np.nonzero(diff[p,:] > 0)[0]
        note_offs = np.nonzero(diff[p,:] < 0)[0]
        for idx, note_on in enumerate(note_ons):
            velocity = np.mean(clipped[p, note_on:note_offs[idx]]) / 127.
            # Create message events
            on_msg = {u'note': pitch, u'velocity': velocity, u'cmd': 9, u'type': 144, u'channel': COMP_CHANNEL}
            events[note_ons[idx]].append(on_msg)
            if note_offs[idx] < num_ticks and not is_onsets_matrix:
                off_msg = {u'note': pitch, u'velocity': 0, u'cmd': 9, u'type': 128, u'channel': COMP_CHANNEL}
                events[note_offs[idx]].append(off_msg)
    return events

if __name__ == '__main__':
    # run!
    unit_predictor = unit_predictor.UnitVariationalAutoencoderOnsets()
    app.run(debug=True)