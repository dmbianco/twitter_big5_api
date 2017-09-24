import tweepy
import sys
import os
import requests
import codecs

from utilities import *


UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)


#screen_name = raw_input("Insert a screen name: ")
screen_name = "FinallyMario" # Valid screen_name
#screen_name = "FinallyMariasssdsdasasdads"  # Invalid screen_name


# LOAD DICTIONARIES AND WEIGHTS
en_stemmer = EnglishStemmer()
en_dictionary = load_dictionary(LIWC_DICTIONARY_FILE_EN, en_stemmer)

it_stemmer = ItalianStemmer()
it_dictionary = load_dictionary(LIWC_DICTIONARY_FILE_IT, it_stemmer)

# The order of the B5 weights should be O C E A N for consistency
ocean_weights = load_weights(LIWC_WEIGHTS_FILE)

# Load quantiles
en_quantiles = load_quantiles(EN_QUANTILES_FILE)

it_quantiles = load_quantiles(IT_QUANTILES_FILE)


num_tokens = 1
api = []
credentials_creation(num_tokens,api)
api = api[0]

# Retrieve user's id and language
try:
    user = api.lookup_users(screen_names = [screen_name])[0]
except tweepy.TweepError as err:
    print err[0][0]['message']
    print err[0][0]['code']
    print "Aborted."
    sys.exit(1)

user_lang = user.lang
user_id = user.id_str

# Compute B5
if user_lang == 'it':
    b5_score = timeline_to_b5(user_id, it_quantiles, api, it_dictionary, it_stemmer, ocean_weights, user_lang)
elif user_lang == 'en':
    b5_score = timeline_to_b5(user_id, en_quantiles, api, en_dictionary, en_stemmer, ocean_weights, user_lang)





