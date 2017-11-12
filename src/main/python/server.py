import codecs
import flask
import json
import logging
import os
import requests
import sys
import tweepy

from argparse import ArgumentParser
from flask import Flask, jsonify, request, redirect, render_template

from utilities import *


LIWC_WEIGHTS_FILE = "IBM_weights_2007.csv"

LIWC_DICTIONARY_FILE_EN = "LIWC_en_2007.csv"
LIWC_DICTIONARY_FILE_IT = "LIWC_it_2007.csv"

IT_QUANTILES_FILE = "quantiles_it.csv"
EN_QUANTILES_FILE = "quantiles_en.csv"


app = Flask(__name__)

class B5:
    def __init__(self, api, en_stemmer, it_stemmer, en_dictionary, it_dictionary, en_quantiles, it_quantiles, ocean_weights):
        self.api = api
        self.it_stemmer = it_stemmer
        self.it_dictionary = it_dictionary
        self.it_quantiles = it_quantiles
        self.en_stemmer = en_stemmer
        self.en_dictionary = en_dictionary
        self.en_quantiles = en_quantiles
        self.ocean_weights = ocean_weights


def error_message(msg):
        return {
            "message": msg,
            "status": "error"
        }


@app.route('/api/b5')
def b5():
    global b5
    screen_name = request.args.get('screen_name')

    if not screen_name:
        return json.dumps(error_message("Could not find user screen name (parameter 'screen_name')"))

    # Retrieve user's id and language
    try:
        user = b5.api.lookup_users(screen_names = [screen_name])[0]
    except tweepy.TweepError as err:
        return jsonify(error_message(str(err)))
    
    user_lang = user.lang
    user_id = user.id_str
    
    # Compute B5
    if user_lang == 'it':
        b5_score = timeline_to_b5(user_id, b5.it_quantiles, b5.api, b5.it_dictionary, b5.it_stemmer, b5.ocean_weights, user_lang)
    elif user_lang == 'en':
        b5_score = timeline_to_b5(user_id, b5.en_quantiles, b5.api, b5.en_dictionary, b5.en_stemmer, b5.ocean_weights, user_lang)
    else:
        return jsonify(error_message("Found language {}. Only 'it' and 'en' supported.".format(user_lang)))

    response = {
        "b5": b5_score,
        "user_id": user_id,
        "user_lang": user_lang,
        "user_screen_name": screen_name,
        "status": "ok"
    }
    return jsonify(response)


def main():
    global b5
    parser = ArgumentParser()
    parser.add_argument("-d", "--data_dir", help="Directory where data is stored", default="./data/")
    
    args = parser.parse_args()
    
    # LOAD DICTIONARIES AND WEIGHTS
    en_stemmer = EnglishStemmer()
    en_dictionary = load_dictionary(os.path.join(args.data_dir, LIWC_DICTIONARY_FILE_EN), en_stemmer)
    
    it_stemmer = ItalianStemmer()
    it_dictionary = load_dictionary(os.path.join(args.data_dir, LIWC_DICTIONARY_FILE_IT), it_stemmer)
    
    # The order of the B5 weights should be O C E A N for consistency
    ocean_weights = load_weights(os.path.join(args.data_dir, LIWC_WEIGHTS_FILE))
    
    # Load quantiles
    en_quantiles = load_quantiles(os.path.join(args.data_dir, EN_QUANTILES_FILE))
    
    it_quantiles = load_quantiles(os.path.join(args.data_dir, IT_QUANTILES_FILE))
    
    
    num_tokens = 1
    api = []
    credentials_creation(num_tokens,api)
    api = api[0]

    b5 = B5(api, en_stemmer, it_stemmer, en_dictionary, it_dictionary, en_quantiles, it_quantiles, ocean_weights)

    return app.run(host="0.0.0.0")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.DEBUG)
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    sys.exit(main())
