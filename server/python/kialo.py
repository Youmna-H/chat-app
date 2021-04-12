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

def clean_up_data(path, output_path):
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
				x = re.search("([0-9]+\.[0-9]*)*", parts[0]) #in case line starts with text not id, combine it with the prev text
				if x.span()[0] == 0 and x.span()[1] == 0:
					to_write = to_write.strip() + " " + line
					continue
			to_write += line
	fw = open(output_path, 'w')
	fw.write(to_write)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-pre", "--pre_path", dest="pre_path", type=str, required=False, default="", help="Need to set to python/ when running from the server") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-d", "--dataset", dest="dataset", type=str, choices=["drugs"], required=False, default="drugs", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	# parser.add_argument("-p", "--data_path", dest="data_path", type=str, required=False, default="/Users/youmna/Documents/OUM2021/MoralMazeData/Money", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-m", "--sim_model", dest="sim_model", choices=['word2vec', 'glove', 'tfidf', 'sbert'], type=str, required=False, default="tfidf", help="The similarity model") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-q", "--query", dest="query", type=str, required=True, default="", help="User's query") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-n", "--num_responses", dest="num_responses", type=int, required=False, default=5, help="Number of similar responses to retrieve") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rp", "--responses_per_stance", dest="responses_per_stance", choices = [0,1], type=int, required=False, default=1, help="Set to 1 if you want the number of responses to be per stance") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rr", "--responses_to_response", dest="responses_to_response", choices = ["arg","arg_response"], type=str, required=False, default="arg", help="Set to arg_response if you want to return the responses to the retrieved most similar utterances") #default is false in case of loading a pretrained model, and just testing on test set

	args = parser.parse_args()
	data_path = ""
	vec_path = ""
	stances_path = ""
	start = False
	topic = ""
	vectors, most_similar,  most_similar_pro, most_similar_con = [], [], [], []
	texts = []
	texts_pro = []
	texts_con = []
	query_text =  args.query
	id_to_claim = {}
	responses_to_claims = {}
	lowercase_to_uppercase = {}
	texts_to_stances = {}
	pre_path = args.pre_path
	id_to_stances = {}
	text_to_stance_lower = {}
	# pre_path = ""
	#uncomment to clean up the data and generate "_cleaned" file, clean up is sometimes required because some kialo files have errors (e.g., endline errors)
	# clean_up_data(pre_path + "kialoData/all-drugs-should-be-legalized-7100.txt", pre_path + "kialoData/all-drugs-should-be-legalized-7100_cleaned.txt")
	config_path = pre_path + "kialo_config.json"
	with open(config_path) as f:
		config = json.load(f)
		for c in config["topics"]:
			if args.dataset == c["id"]:
				data_path = pre_path + c["data_path"]
				vec_path  =  pre_path  + c["sbert_path"]
				stances_path =  pre_path + c["stances_path"]
	
	with open(stances_path) as f:
		for line in f:
			parts = line.strip().split('\t')
			id_to_stances[parts[0]] = parts[1]
	
	if data_path == "":
		print("Incorrect topic!!!!")

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
				else:
					lowercase_to_uppercase[text] = parts[2]
				texts.append(text)
				stance = id_to_stances[parts[0]]
				if stance == 'pro':
					texts_pro.append(text)
					text_to_stance_lower[text] = "pro"
				else:
					texts_con.append(text)
					text_to_stance_lower[text] = "con"
				
				responses_to_claims[text] = []
				id_to_claim[parts[0]] = text
				initial_claim_id  = ".".join(parts[0].split(".")[:-2]) + "."
				initial_claim = id_to_claim[initial_claim_id]
				responses_to_claims[initial_claim].append({"stance":parts[1].lower()[:-1],"text":text})
	texts.append(query_text)
	texts_pro.append(query_text)
	texts_con.append(query_text)

	# print(responses_to_claims)
	# print("##########")
	# print(np.max(lens))
	# print(np.mean(lens))

	if args.sim_model == 'sbert':
		infile = open(vec_path,'rb')
		vectors = cPickle.load(infile)
		infile.close()
		if query_text not in vectors:
			vectors[query_text] = utils.get_sbert_vec(query_text)
		if args.responses_per_stance == 0:
			most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
		else:
			vectors_pro = { d: vectors[d] for d in texts_pro }
			most_similar_pro = utils.most_sim_cos(vectors_pro, query_text, args.num_responses)
			vectors_con = { d: vectors[d] for d in texts_con }
			most_similar_con = utils.most_sim_cos(vectors_con, query_text, args.num_responses)
	elif args.sim_model == 'word2vec':
		path = pre_path + "embeddings/GoogleNews-vectors-negative300.bin"
		model = gensim.models.KeyedVectors.load_word2vec_format(path, binary=True)
		vectors = utils.get_vectors(model, texts)
		if args.responses_per_stance == 0:
			most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
		else:
			vectors_pro = { d: vectors[d] for d in texts_pro }
			most_similar_pro = utils.most_sim_cos(vectors_pro, query_text, args.num_responses)
			vectors_con = { d: vectors[d] for d in texts_con }
			most_similar_con = utils.most_sim_cos(vectors_con, query_text, args.num_responses)
	elif args.sim_model == 'glove':
		path = pre_path + "embeddings/glove.840B.300dword2vec.txt"
		# path = '/Users/youmna/Documents/Phd_year2/Coherence_acl/GC_wsj/glove.6B.100d.word2vec.txt'
		model = utils.read_emb_text(path)
		vectors = utils.get_vectors(model, texts)
		if args.responses_per_stance == 0:
			most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
		else:
			vectors_pro = { d: vectors[d] for d in texts_pro }
			most_similar_pro = utils.most_sim_cos(vectors_pro, query_text, args.num_responses)
			vectors_con = { d: vectors[d] for d in texts_con }
			most_similar_con = utils.most_sim_cos(vectors_con, query_text, args.num_responses)
	elif args.sim_model == 'tfidf':
		if args.responses_per_stance == 0:
			most_similar = utils.get_tfidf_sim(texts, args.num_responses, query_text)
		else:
			most_similar_pro = utils.get_tfidf_sim(texts_pro, args.num_responses, query_text)
			most_similar_con = utils.get_tfidf_sim(texts_con, args.num_responses, query_text)

	most_similar_response = []
	most_similar_response_pro = []
	most_similar_response_con = []
	if args.responses_to_response == "arg_response":
		if args.responses_per_stance == 0:
			for claim in most_similar:
				if claim in responses_to_claims:
					for response in responses_to_claims[claim]:
						most_similar_response.append(response["text"])
			most_similar = most_similar_response[-args.num_responses:]
		else:
			for claim in most_similar_pro:
				if claim in responses_to_claims:
					for response in responses_to_claims[claim]:
						stance = text_to_stance_lower[response["text"]]
						if stance == 'pro':
							most_similar_response_pro.append(response["text"])
						else:
							most_similar_response_con.append(response["text"])
			for claim in most_similar_con:
				if claim in responses_to_claims:
					for response in responses_to_claims[claim]:
						stance = text_to_stance_lower[response["text"]]
						if stance == 'pro':
							most_similar_response_pro.append(response["text"])
						else:
							most_similar_response_con.append(response["text"])

			most_similar_pro = most_similar_response_pro[-args.num_responses:]
			most_similar_con = most_similar_response_con[-args.num_responses:]
	
	if args.responses_per_stance == 0:
		most_similar.reverse()
		stances = [text_to_stance_lower[i] for i in most_similar]
		original_uppercase_responses = []
		for r in most_similar:
			original_uppercase_responses.append(lowercase_to_uppercase[r])
	
		most_similar = original_uppercase_responses
		print("###///".join(most_similar) + "$!$!$" + "###///".join(stances))
	else:
		original_uppercase_responses_pro = []
		for r in most_similar_pro:
			original_uppercase_responses_pro.append(lowercase_to_uppercase[r])
		original_uppercase_responses_con = []
		for r in most_similar_con:
			original_uppercase_responses_con.append(lowercase_to_uppercase[r])
		most_similar_pro = original_uppercase_responses_pro
		most_similar_con = original_uppercase_responses_con
		most_similar_pro.reverse()
		most_similar_con.reverse()
		
		pro_str = "###///".join(most_similar_pro) if len(most_similar_pro) > 0 else ""
		con_str = "###///".join(most_similar_con) if len(most_similar_con) > 0 else ""
		print( pro_str + "$!$!$" + con_str)


	# if len(most_similar) == 0:
	# 	most_similar.append("No Matches found!")
	
	

	# print(_id)
	# print('most similar sentence to query:  ')
	

	


