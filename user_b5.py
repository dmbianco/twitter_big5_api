import tweepy
import sys
import os
import requests
import codecs
import timeit

from utilities import *



def score_to_quantile(score, quant):
    for i,x in enumerate(quant):
        if x > score:
            return i


def personalized_score(scores, cuts = [25,75,100]):
    pers_scores = []
    cuts.sort()
    for s in scores:
        for i,cut in enumerate(cuts):
            if s <= cut:
                pers_scores.append(i)
                break
    return pers_scores



UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)

start_time = timeit.default_timer()

#screen_name = raw_input("Insert a screen name: ")
#screen_name = "mafaldina88"
screen_name = "FinallyMario"
#screen_name = "FinallyMariasssdsdasasdads"

# LOAD DICTIONARIES AND WEIGHTS
en_stemmer = EnglishStemmer()
en_dictionary = defaultdict( np.array )
load_dictionary(LIWC_DICTIONARY_FILE_EN, en_stemmer, en_dictionary)

it_stemmer = ItalianStemmer()
it_dictionary = defaultdict( np.array )
load_dictionary(LIWC_DICTIONARY_FILE_IT, it_stemmer, it_dictionary)

# The order of the B5 weights should be O C E A N for consistency
ocean_weights = [np.zeros((DIM_CATEGORIES,), dtype=np.int) for x in range(5)]
load_weights(LIWC_WEIGHTS_FILE, ocean_weights)

# Load quantiles
en_quantiles = {}
load_quantiles(EN_QUANTILES_FILE, en_quantiles)

it_quantiles = {}
load_quantiles(IT_QUANTILES_FILE, it_quantiles)


num_tokens = 1
api = []
credentials_creation(num_tokens,api)
api = api[0]

partial_time = timeit.default_timer()



try:
    user = api.lookup_users(screen_names = [screen_name])[0]
except tweepy.TweepError as err:
    print err[0][0]['message']
    print err[0][0]['code']
    print "Aborted."
    sys.exit(1)

user_lang = user.lang
user_id = user.id_str

if user_lang == 'it':
    b5_score = timeline_to_b5(user_id, api, it_dictionary, it_stemmer, ocean_weights, user_lang)
elif user_lang == 'en':
    b5_score = timeline_to_b5(user_id, api, en_dictionary, en_stemmer, ocean_weights, user_lang)


token_found = b5_score[5]

b5_raw_score = b5_score[:5] / token_found


print "Token found: ", token_found
if token_found < 40:
    print "The number of token found is not sufficient to compute the B5 scores."
elif token_found < MIN_TOKENS:
    print "The number of token found is very small. The B5 scores may be inaccurate."

print "Raw B5 scores: ", b5_raw_score

b5_score_norm = []

for i,x in enumerate(OCEAN_LIST):
    if  user_lang == 'it':
        b5_score_norm.append( score_to_quantile(b5_raw_score[i], it_quantiles[x]) )
    elif  user_lang == 'en':
        b5_score_norm.append( score_to_quantile(b5_raw_score[i], en_quantiles[x]) )
    
print "Quantiles: ", b5_score_norm


print "25-50-25 score: ", personalized_score(b5_score_norm)

end_time = timeit.default_timer()
print "Loading time: {:0.2f} s".format(partial_time - start_time)
print "Total execution time: {:0.2f} s".format(end_time - start_time)
