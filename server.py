import sys
import time

from flask import Flask, render_template, request, redirect, Response
import random, json
import numpy as np

NUM_PITCHES = 128
NUM_TICKS = 96

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
    # mat = np.random.rand(NUM_PITCHES, NUM_TICKS)
    mat = np.zeros((NUM_PITCHES, NUM_TICKS))
    mat[72] = 0.7
    mat[77,:48] = 0.5
    mat[79,48:] = 1
    matrix = np_to_json(mat)
    return matrix

if __name__ == '__main__':
    # run!
    app.run(debug=True)