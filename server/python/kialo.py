import json
import argparse
import os
import gensim
import utils
from nltk.tokenize import word_tokenize
from six.moves import cPickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
np.random.seed(123)

def clean_up_data(path):
	start = False
	endline = False
	to_write = ""
	with open(path) as f:
		for line in f:
			if line.startswith("1. "):
				start = True
				to_write += line
				continue
			if start:
				if line == "\n":
					endline = True
					continue
			if endline:
				to_write = to_write.strip() + " "
				endline = False
			parts = line.split()
			if len(parts) > 0:
				x = re.search("([0-9]+\.[0-9]*)*", parts[0]) #in case line starts with text not id,  combine it with the prev text
				if x.span()[0] == 0 and x.span()[1] == 0:
					to_write = to_write.strip() + " " + line
					continue
			to_write += line
	fw = open("kialoData/all-drugs-should-be-legalized-7100_cleaned.txt", 'w')
	fw.write(to_write)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--dataset", dest="dataset", type=str, choices=["drugs"], required=False, default="drugs", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	# parser.add_argument("-p", "--data_path", dest="data_path", type=str, required=False, default="/Users/youmna/Documents/OUM2021/MoralMazeData/Money", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-m", "--sim_model", dest="sim_model", choices=['word2vec', 'glove', 'tfidf', 'sbert'], type=str, required=False, default="tfidf", help="The similarity model") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-q", "--query", dest="query", type=str, required=True, default="", help="User's query") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-n", "--num_responses", dest="num_responses", type=int, required=False, default=5, help="Number of similar responses to retrieve") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rp", "--responses_per_stance", dest="responses_per_stance", choices = [0,1], type=int, required=False, default=1, help="Set to 1 if you want the number of responses to be per stance") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rr", "--responses_to_response", dest="responses_to_response", choices = ["arg","arg_response"], type=str, required=False, default="arg", help="Set to arg_response if  we want to retrieve the response to the most similar utterance") #default is false in case of loading a pretrained model, and just testing on test set

	args = parser.parse_args()
	data_path = ""
	start = False
	topic = ""
	vectors, most_similar = [], []
	texts = []
	query_text =  args.query
	id_to_claim = {}
	responses_to_claims = {}
	pre_path = "python/"
	# pre_path = ""
	if args.dataset == "drugs":
		data_path = pre_path + "kialoData/all-drugs-should-be-legalized-7100_cleaned.txt"
	# clean_up_data(pre_path + "kialoData/all-drugs-should-be-legalized-7100.txt")
	lens = []
	with open(data_path) as f:
		for line in f:
			if line.startswith("1. "):
				start = True
				topic = line.strip().split(" ",1)[1]
				id_to_claim["1."] = topic.lower()
				responses_to_claims[topic.lower()] = []
				continue
			if start and line.strip() != "":
				parts = line.strip().split(" ",2)
				if len(parts) < 3:
					continue
				text = parts[2].lower()
				# words = word_tokenize(text)
				# lens.append(len(words))
				if text.startswith("-> see"):
					ref = text.split()[-1]
					text = id_to_claim[ref]
				texts.append(text)
				responses_to_claims[text] = []
				id_to_claim[parts[0]] = text
				initial_claim_id  = ".".join(parts[0].split(".")[:-2]) + "."
				initial_claim = id_to_claim[initial_claim_id]
				responses_to_claims[initial_claim].append({"stance":parts[1].lower()[:-1],"text":text})
	texts.append(query_text)
	# print(responses_to_claims)
	# print("##########")
	# print(np.max(lens))
	# print(np.mean(lens))

	if args.sim_model == 'sbert':
		path = pre_path + "kialoData/sbert/sbert_vecs_drugs.pkl"
		infile = open(path,'rb')
		vectors = cPickle.load(infile)
		infile.close()
		if query_text not in vectors:
			vectors[query_text] = utils.get_sbert_vec(query_text)
		most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
	elif args.sim_model == 'word2vec':
		path = pre_path + "embeddings/GoogleNews-vectors-negative300.bin"
		model = gensim.models.KeyedVectors.load_word2vec_format(path, binary=True)
		vectors = utils.get_vectors(model, texts)
		most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
	elif args.sim_model == 'glove':
		path = pre_path + "embeddings/glove.840B.300dword2vec.txt"
		# path = '/Users/youmna/Documents/Phd_year2/Coherence_acl/GC_wsj/glove.6B.100d.word2vec.txt'
		model = utils.read_emb_text(path)
		vectors = utils.get_vectors(model, texts)
		most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
	elif args.sim_model == 'tfidf':
		most_similar = utils.get_tfidf_sim(texts, args.num_responses, query_text)

	most_similar_response = []
	if args.responses_to_response == "arg_response":
		for claim in most_similar:
			if claim in responses_to_claims:
				for response in responses_to_claims[claim]:
					most_similar_response.append(response["text"])
		most_similar = most_similar_response[-args.num_responses:]

	most_similar.reverse()
	stances = ["neutral"]*args.num_responses
	# print(_id)
	# print('most similar sentence to query:  ')
	print("###///".join(most_similar) + "$!$!$" + "###///".join(stances))


