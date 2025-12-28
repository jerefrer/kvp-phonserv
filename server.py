from flask import Flask, json, request
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../bophono')))
from phonetics import segmentbywords, segmentbytwo, segmentbyone, add_phono
from flask_cors import CORS

api = Flask("KVP", static_url_path='', static_folder='web/')
CORS(api)

def _get_sanskrit_options():
    """Extract Sanskrit options from request form data."""
    sanskrit_mode = request.form.get('sanskrit_mode', None)
    anusvara_style = request.form.get('anusvara_style', 'ṃ')
    return sanskrit_mode, anusvara_style

@api.route('/segmentbywords', methods=['POST'])
def segment_and_phon():
    in_str = request.form['str']
    sanskrit_mode, anusvara_style = _get_sanskrit_options()
    seg = segmentbywords(in_str)
    res = { "segmented" : seg }
    add_phono(seg, res, sanskrit_mode=sanskrit_mode, anusvara_style=anusvara_style)
    return json.dumps(res, ensure_ascii=False)

@api.route('/segmentbyone', methods=['POST'])
def segmentbyone_and_phon():
    in_str = request.form['str']
    sanskrit_mode, anusvara_style = _get_sanskrit_options()
    seg = segmentbyone(in_str)
    res = { "segmented" : seg }
    add_phono(seg, res, sanskrit_mode=sanskrit_mode, anusvara_style=anusvara_style)
    return json.dumps(res, ensure_ascii=False)

@api.route('/segmentbytwo', methods=['POST'])
def segmentbytwo_and_phon():
    in_str = request.form['str']
    sanskrit_mode, anusvara_style = _get_sanskrit_options()
    seg = segmentbytwo(in_str)
    res = { "segmented" : seg }
    add_phono(seg, res, sanskrit_mode=sanskrit_mode, anusvara_style=anusvara_style)
    return json.dumps(res, ensure_ascii=False)

@api.route('/phoneticize', methods=['POST'])
def phon():
    in_str = request.form['str']
    sanskrit_mode, anusvara_style = _get_sanskrit_options()
    res = {}
    add_phono(in_str, res, sanskrit_mode=sanskrit_mode, anusvara_style=anusvara_style)
    return json.dumps(res, ensure_ascii=False)

@api.route('/', methods=['GET'])
def default():
    return api.send_static_file('index.html')
