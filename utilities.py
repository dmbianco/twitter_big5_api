import sys
import os
import tweepy
import requests
import re
import csv
import datetime
import time
from collections import defaultdict
from nltk.stem.snowball import ItalianStemmer
from nltk.stem.snowball import EnglishStemmer
import numpy as np

from token_2 import *


OCEAN_LIST = [ch for ch in "OCEAN"]

LIWC_WEIGHTS_FILE = "IBM_weights_2007.csv"

LIWC_DICTIONARY_FILE_EN = "LIWC_en_2007.csv"
LIWC_DICTIONARY_FILE_IT = "LIWC_it_2007.csv"

IT_QUANTILES_FILE = "quantiles_it.csv"
EN_QUANTILES_FILE = "quantiles_en.csv"

MIN_TOKENS = 70
DIM_CATEGORIES = 64

requests.packages.urllib3.disable_warnings()

# Regex used for parsing tweets
rule_mentions = re.compile(r"(?<=^|(?<=[^a-zA-Z0-9-_\.]))@(_?[A-Za-z0-9]+[A-Za-z0-9_]+)")
rule_hash = re.compile(r"(?<=^|(?<=[^a-zA-Z0-9-_\.]))#([A-Za-z]+[A-Za-z0-9]+)")
rule_url = re.compile(r"https?\S+")
rule_numbers = re.compile(r"\d+")


def credentials_creation(num_tokens,api,dont_check = True):
	i = 0
	for y in tokens:
		x = token_class(tokens[y],y)
		auth = tweepy.OAuthHandler(x.consumer_key, x.consumer_secret)
		auth.secure = True
		auth.set_access_token(x.access_token, x.access_token_secret)
		tweepy_api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
		if dont_check or check_credential(tweepy_api):
			api.append(tweepy_api)
			i += 1
		else:
			print "Error: account num",x.key,"not connected"
	return i


def check_credential(api):
	try:
		me_medesimo = api.me()
		print (me_medesimo.name) + " is connected!"
		return True
	except:
		return False


def tweet_get_fields(tweet):
	return [ unicode(tweet.lang).encode('utf-8'),
			 unicode(tweet.text).encode('utf-8') ] 


class Word:
    # class used for loading the dictionaries
	features = {}
	translation = str()
	
	def __init__(self,not_stemmed,f,tr=""):
		self.features = f
		self.translation = tr
		self.not_stemmed=not_stemmed


def load_dictionary(liwc_dictionary_file, stemmer):
	# Given the name of the file with the LIWC dictionary and a stemmer, it returns a 
    # dictionary whose keys are the words and whose values are objects of class Word, 
    # i.e. they contain the LIWC features.
	word_dictionary = defaultdict( np.array )
	with open(liwc_dictionary_file, "rb") as file_reader:
		csv_reader=csv.reader(file_reader)
		i = 0
		for row in csv_reader:
			not_stemmed=row[0].decode("utf-8")
			if sum(np.array(row[2:]).astype(int))>0:
				word_dictionary[stemmer.stem(not_stemmed.strip())] = Word(not_stemmed, np.array(row[2:], dtype=np.int), row[1])
	return word_dictionary


def load_weights(liwc_weights_file):
    # Given the file with the weights, it loads them into a numpy matrix
	ocean_weights = [np.zeros((DIM_CATEGORIES,), dtype=np.int) for x in range(5)]
	with open(liwc_weights_file, "rb") as file_reader:
		csv_reader=csv.reader(file_reader, delimiter=",")
		csv_reader.next()
		i = 0
		for row in csv_reader:
			ocean_weights[i] = (np.array(row[1:], dtype=np.float) )
			i += 1
	return ocean_weights


def load_quantiles(quantiles_file):
    # Given the file with the quantiles, it loads them into a dictionary whose keys
    # are the OCEAN traits and whose keys are the quantiles.
    quantiles = {}
    with open(quantiles_file, 'rb') as f:
        reader = csv.reader(f)
        reader.next()
        for row in reader:
            quantiles[row[0]] = [ float(x) for x in row[1:] ]
    return quantiles


def tweet_to_b5(text, word_dictionary, stemmer, ocean):
	# Given a tweet (not a retweet), it computes the b5 score associated to it
    # and the number of tokens found in it
	if text[0:4] == "RT @":
		return np.zeros((6,), dtype=np.float)
	
	text = re.sub(rule_numbers,"",text) #removing first numbers seems to be faster, but consider that hashtags and mentions CANNOT be extracted.
	text = re.sub(rule_url," ",text)
	text = re.sub(rule_hash," ",text)
	text = re.sub(rule_mentions," ",text)
	
	
	text_toknzd = map(lambda x: stemmer.stem(x), re.findall(r'\w+', text.decode("utf-8").lower(), flags=re.UNICODE))
	
	token_found = 0
	liwc_categories = np.zeros((DIM_CATEGORIES,), dtype=np.int)
	
	for t in text_toknzd:
		if t in word_dictionary:
			liwc_categories += word_dictionary[t].features
			token_found += 1
	
	b5 = np.zeros((5,), dtype=np.float)
	
	for i,x in enumerate(ocean):
		b5[i] = np.dot(liwc_categories,x)
	
	# 5 b5 features + number of tokens found
	b5 = np.append(b5,token_found)
	
	return b5


def score_to_quantile(score, quant):
    # Given a score (single number) and a list with quantiles, it returns its correct
    # quantile.
    for i,x in enumerate(quant):
        if x > score:
            return i


def personalized_score(scores, cuts = [25,75,100]):
    # Given a list of scores and a list with cuts, it returns the bins into which they
    # fall. For example, considering a single score [30] and the default cuts, the
    # function returns 1; if it were [80], it would return 2.
    pers_scores = []
    cuts.sort()
    for s in scores:
        for i,cut in enumerate(cuts):
            if s <= cut:
                pers_scores.append(i)
                break
    return pers_scores


def timeline_to_b5(user_id, quantiles, api, word_dictionary, stemmer, ocean, lang):
    # Given a user id, a dictionary and a stemmer, it computes the big five scores
    # of the user after having downloaded her tweets.
	tweets_per_request = 200
	max_pages = 30
	b5_score = np.zeros((6,), dtype=np.float)
	try:
		cur = tweepy.Cursor(api.user_timeline, id = user_id, count = tweets_per_request)

		timeline = [page for page in cur.pages(max_pages)]
		
		num_tweets = 0
		for page in timeline:
			num_tweets += len(page)
		if num_tweets <= 10:
			return b5_score
		
		for page in timeline:
			for tweet in page:
				tw = tweet_get_fields(tweet)
				if tw[0] == lang:
					b5_score += tweet_to_b5(tw[1], word_dictionary, stemmer, ocean)

		del timeline
	
	except tweepy.TweepError as err:
		print err[0][0]['message']
		print err[0][0]['code']
	
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
		b5_score_norm.append( score_to_quantile(b5_raw_score[i], quantiles[x]) )
		
	print "Quantiles: ", b5_score_norm

	print "25-50-25 score: ", personalized_score(b5_score_norm)

	return b5_score_norm

	
