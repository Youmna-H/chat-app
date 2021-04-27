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
import faiss_index
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
	import time
	start = time.time()
	parser = argparse.ArgumentParser()
	parser.add_argument("-pre", "--pre_path", dest="pre_path", type=str, required=False, default="", help="Need to set to python/ when running from the server") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-d", "--dataset", dest="dataset", type=str, required=False, default="drugs", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	# parser.add_argument("-p", "--data_path", dest="data_path", type=str, required=False, default="/Users/youmna/Documents/OUM2021/MoralMazeData/Money", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-m", "--sim_model", dest="sim_model", choices=['word2vec', 'glove', 'tfidf', 'sbert'], type=str, required=False, default="tfidf", help="The similarity model") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-q", "--query", dest="query", type=str, required=True, default="", help="User's query") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-n", "--num_responses", dest="num_responses", type=int, required=False, default=5, help="Number of similar responses to retrieve") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rp", "--responses_per_stance", dest="responses_per_stance", choices = [0,1], type=int, required=False, default=1, help="Set to 1 if you want the number of responses to be per stance") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rr", "--responses_to_response", dest="responses_to_response", choices = ["arg","arg_response"], type=str, required=False, default="arg", help="Set to arg_response if you want to return the responses to the retrieved most similar utterances") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-i", "--indexed", dest="is_indexed", type=int, required=False, default=1, help="Set to 0 if you don't want to use faiss indexing") #default is false in case of loading a pretrained model, and just testing on test set

	args = parser.parse_args()
	data_path_pro = ""
	data_path_con = ""
	data_path_all = ""
	vec_path_pro = ""
	vec_path_con = ""
	vec_path_pro_original = ""
	vec_path_con_original = ""
	vec_path_all = ""
	responses = {}
	stances = {}

	topic = ""
	vectors, most_similar,  most_similar_pro, most_similar_con = [], [], [], []
	texts_all = []
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
	# clean_up_data(pre_path + "kialoData/should-a-license-be-required-in-order-to-have-a-child-procreate-2368.txt", pre_path + "kialoData/should-a-license-be-required-in-order-to-have-a-child-procreate-2368_cleaned.txt")
	config_path = pre_path + "kialo_config.json"
	with open(config_path) as f:
		config = json.load(f)
		for c in config["topics"]:
			if args.dataset == c["id"]:
				data_path_pro = pre_path + c["data_path_pro"]
				vec_path_pro = pre_path  + c["sbert_path_pro"]
				data_path_con = pre_path + c["data_path_con"]
				vec_path_con = pre_path  + c["sbert_path_con"]
				data_path_all = pre_path + c["data_path_all"]
				vec_path_all = pre_path  + c["sbert_path_all"]
				vec_path_pro_original = pre_path  + c["sbert_path_pro_original"]
				vec_path_con_original = pre_path  + c["sbert_path_con_original"]
	
	#read data files
	if args.responses_per_stance == 0:
		with open(data_path_all) as f:
			for line in f:
				parts = line.strip().split("\t",4)
				text = parts[0]
				lowercase_to_uppercase[text] = parts[2]
				texts_all.append(text)
				if len(parts) >= 5:
					responses[text] = parts[4].split('\t')
				stances[text] = parts[3]
				# texts_all.append(query_text)
	else:
		with open(data_path_pro) as f:
			for line in f:
				parts = line.strip().split("\t",4)
				text = parts[0]
				lowercase_to_uppercase[text] = parts[2]
				texts_pro.append(text)
				if len(parts) >= 5:
					responses[text] = parts[4].split('\t')
		with open(data_path_con) as f:
			for line in f:
				parts = line.strip().split("\t",4)
				text = parts[0]
				lowercase_to_uppercase[text] = parts[2]
				texts_con.append(text)
				if len(parts) >= 5:
					responses[text] = parts[4].split('\t')
		# texts_pro.append(query_text)
		# texts_con.append(query_text)
	query_text = query_text.lower()
	if args.sim_model == 'sbert':
		query_vec = utils.get_sbert_vec(query_text)
		if args.is_indexed == 1:
			query_vec /= np.linalg.norm(query_vec, keepdims=True)
			if args.responses_per_stance == 0:
				most_similar = faiss_index.search(vec_path_all, query_vec, texts_all, args.num_responses)
				#hack reverse here because it is returned in the correct order and it get reversed later
				most_similar.reverse()
			else:
				most_similar_pro = faiss_index.search(vec_path_pro, query_vec, texts_pro, args.num_responses)
				most_similar_con = faiss_index.search(vec_path_con, query_vec, texts_con, args.num_responses)
				#hack reverse here because it is returned in the correct order and it get reversed later
				most_similar_pro.reverse()
				most_similar_con.reverse()
		else:
			vectors, vectors_pro, vectors_con = {}, {}, {}
			# 	for bert_path in vec_path:
			infile_pro = open(vec_path_pro_original,'rb')
			infile_con = open(vec_path_con_original,'rb')
			if args.responses_per_stance == 0:
				vectors[query_text] = query_vec
				vectors.update(cPickle.load(infile_pro))
				vectors.update(cPickle.load(infile_con))
				most_similar.extend(utils.most_sim_cos(vectors, query_text, args.num_responses))
			else:
				vectors_pro[query_text] = query_vec
				vectors_con[query_text] = query_vec
				vectors_pro.update(cPickle.load(infile_pro))
				vectors_con.update(cPickle.load(infile_con))
				most_similar_pro.extend(utils.most_sim_cos(vectors_pro, query_text, args.num_responses))
				most_similar_con.extend(utils.most_sim_cos(vectors_con, query_text, args.num_responses))
			infile_pro.close()
			infile_con.close()
		
	elif args.sim_model == 'word2vec':
		path = pre_path + "embeddings/GoogleNews-vectors-negative300.bin"
		model = gensim.models.KeyedVectors.load_word2vec_format(path, binary=True)
		texts_all.append(query_text)
		if args.responses_per_stance == 0:
			vectors = utils.get_vectors(model, texts_all)
			most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
		else:
			texts_pro.append(query_text)
			texts_con.append(query_text)
			vectors_pro = utils.get_vectors(model, texts_pro)
			most_similar_pro = utils.most_sim_cos(vectors_pro, query_text, args.num_responses)
			vectors_con = utils.get_vectors(model, texts_con)
			most_similar_con = utils.most_sim_cos(vectors_con, query_text, args.num_responses)
	elif args.sim_model == 'glove':
		path = pre_path + "embeddings/glove.840B.300dword2vec.txt"
		# path = '/Users/youmna/Documents/Phd_year2/Coherence_acl/GC_wsj/glove.6B.100d.word2vec.txt'
		model = utils.read_emb_text(path)
		texts_all.append(query_text)
		if args.responses_per_stance == 0:
			vectors = utils.get_vectors(model, texts_all)
			most_similar = utils.most_sim_cos(vectors, query_text, args.num_responses)
		else:
			texts_pro.append(query_text)
			texts_con.append(query_text)
			vectors_pro = utils.get_vectors(model, texts_pro)
			most_similar_pro = utils.most_sim_cos(vectors_pro, query_text, args.num_responses)
			vectors_con = utils.get_vectors(model, texts_con)
			most_similar_con = utils.most_sim_cos(vectors_con, query_text, args.num_responses)
	elif args.sim_model == 'tfidf':
		if args.responses_per_stance == 0:
			texts_all.append(query_text)
			most_similar = utils.get_tfidf_sim(texts_all, args.num_responses, query_text)
		else:
			texts_pro.append(query_text)
			texts_con.append(query_text)
			most_similar_pro = utils.get_tfidf_sim(texts_pro, args.num_responses, query_text)
			most_similar_con = utils.get_tfidf_sim(texts_con, args.num_responses, query_text)

	most_similar_response = []
	most_similar_response_pro = []
	most_similar_response_con = []
	if args.responses_to_response == "arg_response":
		if args.responses_per_stance == 0:
			for claim in most_similar:
				if claim in responses:
					most_similar_response.extend(responses[claim])
			most_similar = most_similar_response[-args.num_responses:]
		else:
			for claim in most_similar_pro:
				if claim in responses:
					for response in responses[claim]:
						if response in most_similar_pro:
							most_similar_response_pro.append(response)
						else:
							most_similar_response_con.append(response)
			for claim in most_similar_con:
				if claim in responses:
					for response in responses[claim]:
						if response in most_similar_pro:
							most_similar_response_pro.append(response)
						else:
							most_similar_response_con.append(response)

			most_similar_pro = most_similar_response_pro[-args.num_responses:]
			most_similar_con = most_similar_response_con[-args.num_responses:]
	
	if args.responses_per_stance == 0:
		most_similar.reverse()
		_stances = [stances[i.lower()] for i in most_similar]
		original_uppercase_responses = []
		if args.responses_to_response != "arg_response":
			for r in most_similar:
				original_uppercase_responses.append(lowercase_to_uppercase[r])
			most_similar = original_uppercase_responses
		print("###///".join(most_similar) + "$!$!$" + "###///".join(_stances))

	else:
		if args.responses_to_response != "arg_response":
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

	done = time.time()
	# print("time:" + str(done - start))
	


