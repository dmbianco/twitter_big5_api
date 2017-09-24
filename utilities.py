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


sys.path.insert(0,'/home/domenico/Desktop/WORK/TWITTER/TOKEN/')
from token_2 import *

OCEAN_LIST = [ch for ch in "OCEAN"]

LIWC_WEIGHTS_FILE = "IBM_weights_2007.csv"

LIWC_DICTIONARY_FILE_EN = "LIWC_en_2007.csv"
LIWC_DICTIONARY_FILE_IT = "LIWC_it_2007.csv"

IT_QUANTILES_FILE = "quantiles_it.csv"
EN_QUANTILES_FILE = "quantiles_en.csv"

MIN_TOKENS = 70
DIM_CATEGORIES = 64


rule_mentions = re.compile(r"(?<=^|(?<=[^a-zA-Z0-9-_\.]))@(_?[A-Za-z0-9]+[A-Za-z0-9_]+)")
rule_hash = re.compile(r"(?<=^|(?<=[^a-zA-Z0-9-_\.]))#([A-Za-z]+[A-Za-z0-9]+)")
rule_url = re.compile(r"https?\S+")
rule_numbers = re.compile(r"\d+")

requests.packages.urllib3.disable_warnings()

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
	features = {}
	translation = str()
	
	def __init__(self,not_stemmed,f,tr=""):
		self.features = f
		self.translation = tr
		self.not_stemmed=not_stemmed


def load_dictionary(liwc_dictionary_file, stemmer, word_dictionary):
	with open(liwc_dictionary_file, "rb") as file_reader:
		csv_reader=csv.reader(file_reader)
		i = 0
		for row in csv_reader:
			not_stemmed=row[0].decode("utf-8")
			if sum(np.array(row[2:]).astype(int))>0:
				word_dictionary[stemmer.stem(not_stemmed.strip())] = Word(not_stemmed, np.array(row[2:], dtype=np.int), row[1])
	


def load_weights(liwc_weights_file, ocean):
	with open(liwc_weights_file, "rb") as file_reader:
		csv_reader=csv.reader(file_reader, delimiter=",")
		csv_reader.next()
		i = 0
		for row in csv_reader:
			ocean[i] = (np.array(row[1:], dtype=np.float) )
			i += 1


def load_quantiles(quantiles_file, quantiles):
    with open(quantiles_file, 'rb') as f:
        reader = csv.reader(f)
        reader.next()
        for row in reader:
            quantiles[row[0]] = [ float(x) for x in row[1:] ]


def tweet_to_b5(text, word_dictionary, stemmer, ocean):
	
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
	

def timeline_to_b5(user_id, api, word_dictionary, stemmer, ocean, lang):
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
#				if "401" in err.reason:
		print err.reason
	
	#				if "[Errno -3]" in err.reason:
	#					print "Connection error!"
	
	return b5_score



	
