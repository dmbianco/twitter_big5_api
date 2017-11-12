tokens = {

"0" : {
"consumer_key" : "Qy1okV5soJ3Rresd3axxuoz0r",
"consumer_secret" : "1VjuiDXGPG5O4nWxvsJBvHD5n2AiJW7NITcIvzfrNixG6IExZA",
"access_token" : "847155822186692608-QAS6AoOO6qrgx7LfCbYqgpcMqqWGE0W",
"access_token_secret" : "3rzjso0nm2XpbsN7Owiiy6O8mNGvJWmnXXJLUZe3L3pGc"
}

}


class token_class():
	def __init__(self, dic, key_d):
		self.key = key_d
		self.consumer_key = dic["consumer_key"]
		self.consumer_secret = dic["consumer_secret"]
		self.access_token = dic["access_token"]
		self.access_token_secret = dic["access_token_secret"]




