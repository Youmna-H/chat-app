import json
import argparse
import os
import gensim
import utils
from six.moves import cPickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
#import faiss_index
import collections
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

def load(topic, model_name, sub_model_name="paraphrase-distilroberta-base-v1", is_indexed=False, **kwargs):
	pre_path = ""#"python/"
	config_path = pre_path + "kialo_config.json"
	data_path_pro, vec_path_pro, data_path_con, vec_path_con, data_path_all, vec_path_all, vec_path_pro_original, vec_path_con_original = "", "", "", "", "", "", "", ""
	lowercase_to_uppercase = {}
	texts_all, texts_pro, texts_con = [], [], []
	stances = {}
	responses = {}
	with open(config_path) as f:
		config = json.load(f)
		for c in config["topics"]:
			if topic == c["id"]:
				data_path_pro = pre_path + c["data_path_pro"]
				vec_path_pro = pre_path  + c["sbert_path_pro"]
				data_path_con = pre_path + c["data_path_con"]
				vec_path_con = pre_path  + c["sbert_path_con"]
				data_path_all = pre_path + c["data_path_all"]
				vec_path_all = pre_path  + c["sbert_path_all"]
				vec_path_pro_original = pre_path  + c["sbert_path_pro_original"]
				vec_path_con_original = pre_path  + c["sbert_path_con_original"]
	#read data files
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
	#load model
	pro_vecs, con_vecs = [], []
	model = None
	if model_name == 'sbert':
		model = utils.get_sbert_model(sub_model_name)
		if is_indexed == 1:
			models_pro_con = [faiss_index.load_index(vec_path_pro), faiss_index.load_index(vec_path_con)]
		else:
			infile_pro = open(vec_path_pro_original,'rb')
			infile_con = open(vec_path_con_original,'rb')
			pro_vecs = cPickle.load(infile_pro)
			con_vecs = cPickle.load(infile_con)
			model = utils.get_sbert_model(sub_model_name)
	elif model_name == 'word2vec':
		path = pre_path + "embeddings/GoogleNews-vectors-negative300.bin"
		model = gensim.models.KeyedVectors.load_word2vec_format(path, binary=True)
		pro_vecs, model = utils.get_vectors(model, texts_pro)
		con_vecs, model = utils.get_vectors(model, texts_con)
	elif model_name == 'glove':
		path = pre_path + "embeddings/glove.840B.300dword2vec.txt"
		model = utils.read_emb_text(path)
		pro_vecs, model = utils.get_vectors(model, texts_pro)
		con_vecs, model = utils.get_vectors(model, texts_con)
	#return values
	#model is an object
	#pro_vecs, con_vecs are arrays of vectors
	#texts_pro, texts_con are arrays of texts
	#responses and lowercase_to_uppercase is a dictionaries
	return {"model": model, "pro_vecs":pro_vecs, "con_vecs":con_vecs, "texts_pro":texts_pro, "texts_con":texts_con, "responses":responses, "lowercase_to_uppercase":lowercase_to_uppercase}

def calculate_parent_sim(query, model_name, model, pro_vecs, con_vecs, texts_pro, texts_con, responses, lowercase_to_uppercase, num_responses=5, classify_responses=True, responses_to_response=False, is_indexed=False, **kwargs):
	parents = {}
	for t in texts_pro:
		if t in responses:
			for r in responses[t]:
				parents[r.lower()] = t.lower()
	for t in texts_con:
		if t in responses:
			for r in responses[t]:
				parents[r.lower()] = t.lower()

	all_vecs = pro_vecs
	all_vecs.update(con_vecs)
	sim_map = {}
	output = collections.OrderedDict()
	for r in parents:
		v1 = np.array(all_vecs[r].reshape(1,-1))
		for t in all_vecs:
			if t == r:
				continue
			v2 = np.array(all_vecs[t].reshape(1,-1))
			sim = cosine_similarity(v1, v2)[0][0]
			is_parent = parents[r] == t
			if r not in sim_map:
				sim_map[r] = []
			sim_map[r].append({"text":t, "sim":sim, "is_parent":is_parent})

	parent_ranks = []
	other_ranks = []
	all_ranks = []
	parent_sim = []
	other_sim = []
	all_sim = []
	for r in sim_map:
		newlist = sorted(sim_map[r], key=lambda k: k['sim'], reverse=True) 
		# sim_map[r] = newlist
		for i, item in enumerate(newlist):
			if item['is_parent']:
				#paraphrase-distilroberta-base-v1
				parent_ranks.append(i) 
				parent_sim.append(item['sim']) 
				# print("%i/%i" % (i, len(newlist)))
			else:
				other_ranks.append(i) 
				other_sim.append(item['sim']) 
			all_ranks.append(i) #356.894024
			all_sim.append(item['sim']) #0.296818

	print("# parent child comparisons = %f" % len(parent_ranks))
	print("# other comparisons = %f" % len(other_ranks))
	print("parent mean rank = %f" % np.mean(parent_ranks)) #75.561181
	print("other mean rank = %f" % np.mean(other_ranks)) #356.894024
	print("all mean rank = %f" % np.mean(all_ranks)) #356.500000
	print("parent mean sim = %f" % np.mean(parent_sim)) #0.495087
	print("other mean sim = %f" % np.mean(other_sim)) #0.296818
	print("all mean sim = %f" % np.mean(all_sim)) #0.297096


def get_suggested_responses(query, model_name, model, pro_vecs, con_vecs, texts_pro, texts_con, responses, lowercase_to_uppercase, num_responses=5, classify_responses=True, responses_to_response=False, is_indexed=False, **kwargs):
	pre_path = ""#"python/"
	# import time
	# start = time.time()
	config_path = pre_path + "kialo_config.json"
	most_similar, stances = [], []
	distances_pro, distances_con, most_similar_pro, most_similar_con = [], [], [], []
	query_text = query.lower()
	query_vec = []
	
	if model_name == 'tfidf':
		texts_pro.append(query_text)
		texts_con.append(query_text)
		distances_pro, most_similar_pro = utils.get_tfidf_sim(texts_pro, num_responses, query_text)
		distances_con, most_similar_con = utils.get_tfidf_sim(texts_con, num_responses, query_text)
	else:
		if model_name == 'sbert':
			query_vec = utils.get_sbert_vec(model, query_text)
		else:
			query_vec = utils.get_vector(model, query_text)
		if model_name == 'sbert' and is_indexed:
			query_vec /= np.linalg.norm(query_vec, keepdims=True)
			distances_pro, most_similar_pro = faiss_index.search(pro_vecs, query_vec, texts_pro, num_responses)
			distances_con, most_similar_con = faiss_index.search(con_vecs, query_vec, texts_con, num_responses)
		else:
			if model_name == 'sbert' and False: #add check encoder check instead of false
				distances_pro, most_similar_pro = utils.get_sbert_mostsimilar_crossencoder(pro_vecs, query_text, query_vec, num_responses)
				distances_con, most_similar_con = utils.get_sbert_mostsimilar_crossencoder(con_vecs, query_text, query_vec, num_responses)
				print(distances_pro)
			else:
				distances_pro, most_similar_pro = utils.most_sim_cos(pro_vecs, query_vec, num_responses)
				distances_con, most_similar_con = utils.most_sim_cos(con_vecs, query_vec, num_responses)
	stances = ["pro"] * len(most_similar_pro)
	stances.extend(["con"] * len(most_similar_con))
	most_similar = most_similar_pro
	most_similar.extend(most_similar_con) 
	distances = distances_pro
	distances.extend(distances_con)
	if not classify_responses:
		distances, most_similar, stances = zip(*sorted(zip(distances, most_similar, stances), reverse=True))
		most_similar = most_similar[:num_responses]
		stances = stances[:num_responses]

	if responses_to_response:
		stances = []
		most_similar_response = []
		for claim in most_similar:
			if claim in responses:
				for response in responses[claim]:
					r = response.lower()
					most_similar_response.append(r)
					if r in texts_pro:
						stances.append('pro')
					else:
						stances.append('con')
		if classify_responses:
			most_similar = []
			temp_stances = []
			pro_count, con_count = 0, 0
			for i, claim in enumerate(most_similar_response):
				if stances[i] == 'pro' and pro_count < num_responses:
					most_similar.append(claim)
					pro_count += 1
					temp_stances.append('pro')
				elif stances[i] == 'con' and con_count < num_responses:
					most_similar.append(claim)
					con_count += 1
					temp_stances.append('con')
			stances = temp_stances
		else:
			most_similar = most_similar_response[:num_responses]
			stances = stances[:num_responses]
	
	#format return values
	return_array = []
	for i, text in enumerate(most_similar):
		return_array.append({"text": lowercase_to_uppercase[text], "stance": stances[i]})

	#format of returned value
	# {
	# 	"suggested_responses": [
	# 		{
	# 			"text": text1,
	# 			"stance": stance1
	# 		},
	# 		{
	# 			"text": text2,
	# 			"stance": stance2
	# 		}
	# 	]
	# }
	return json.dumps({"suggested_responses": return_array})

	# done = time.time()
	# print("time:" + str(done - start))
	

if __name__ == "__main__":
	model_name = "sbert"
	query = "Vaccination will help build immunity against the virus and save lives."
	is_indexed = False
	num_responses = 3
	classify_responses = True
	responses_to_response = False
	topic = "vaccination"

	loaded_values = load(topic, model_name, is_indexed=is_indexed)
	print("loaded")
	x = get_suggested_responses(query, model_name, loaded_values['model'], loaded_values['pro_vecs'], loaded_values['con_vecs'],
	loaded_values['texts_pro'], loaded_values['texts_con'], loaded_values['responses'], loaded_values['lowercase_to_uppercase'],
	 num_responses=num_responses, classify_responses=classify_responses, responses_to_response=responses_to_response, is_indexed=is_indexed)
	# calculate_parent_sim(query, model_name, loaded_values['model'], loaded_values['pro_vecs'], loaded_values['con_vecs'],
	# loaded_values['texts_pro'], loaded_values['texts_con'], loaded_values['responses'], loaded_values['lowercase_to_uppercase'],
	#  num_responses=100, classify_responses=False, responses_to_response=responses_to_response, is_indexed=is_indexed)
	print(x) 
