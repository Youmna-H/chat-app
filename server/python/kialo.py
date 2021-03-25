import json
import argparse
import os
import gensim
import utils
from nltk.tokenize import word_tokenize

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

np.random.seed(123)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--dataset", dest="dataset", type=str, choices=["drugs"], required=False, default="drugs", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	# parser.add_argument("-p", "--data_path", dest="data_path", type=str, required=False, default="/Users/youmna/Documents/OUM2021/MoralMazeData/Money", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-m", "--sim_model", dest="sim_model", choices=['word2vec', 'glove', 'tfidf'], type=str, required=False, default="tfidf", help="The similarity model") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-q", "--query", dest="query", type=str, required=True, default="", help="User's query") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-n", "--num_responses", dest="num_responses", type=int, required=False, default=5, help="Number of similar responses to retrieve") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rp", "--responses_per_stance", dest="responses_per_stance", choices = [0,1], type=int, required=False, default=1, help="Set to true if you want the number of responses to be per stance") #default is false in case of loading a pretrained model, and just testing on test set
	
	args = parser.parse_args()
	data_path = ""
	start = False
	topic = ""
	vectors, most_similar = [], []
	texts = []
	text =  args.query
	pre_path = "python/"
	# pre_path = ""
	if args.dataset == "drugs":
		data_path = pre_path + "kialoData/all-drugs-should-be-legalized-7100.txt"
	with open(data_path) as f:
		for line in f:
			if line.startswith("1. "):
				start = True
				topic = line.strip().split(" ",1)[1]
				continue
			if start and line.strip() != "":
				parts = line.strip().split(" ",2)
				if len(parts) < 3:
					continue
				texts.append(parts[2].lower())

	texts.append(text)

	if args.sim_model == 'word2vec':
		path = pre_path + "embeddings/GoogleNews-vectors-negative300.bin"
		model = gensim.models.KeyedVectors.load_word2vec_format(path, binary=True)
		vectors = utils.get_vectors(model, texts)
		most_similar = utils.most_sim_cos(vectors, text, args.num_responses)
	elif args.sim_model == 'glove':
		path = pre_path + "embeddings/glove.840B.300dword2vec.txt"
		# path = '/Users/youmna/Documents/Phd_year2/Coherence_acl/GC_wsj/glove.6B.100d.word2vec.txt'
		model = utils.read_emb_text(path)
		vectors = utils.get_vectors(model, texts)
		most_similar = utils.most_sim_cos(vectors, text, args.num_responses)
	elif args.sim_model == 'tfidf':
		most_similar = utils.get_tfidf_sim(texts, args.num_responses, text)

	most_similar.reverse()
	stances = ["neutral"]*args.num_responses
	# print(_id)
	# print('most similar sentence to query:  ')
	print("###///".join(most_similar) + "$!$!$" + "###///".join(stances))


