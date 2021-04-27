import numpy as np
import faiss 
from six.moves import cPickle
import re
import json
from sklearn.preprocessing import normalize

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


def parse_bert(data_path, sbert_path_pro_original, sbert_path_con_original):
	id_to_stances = {}
	sents_lower_pro = []
	sents_lower_con = []
	sents_map = {}
	id_to_text = {}
	x = 0
	for file_index, path in enumerate(data_path):
		start = False
		with open(path) as f:
			for line in f:
				# if x == 100:
				# 	break
				x += 1
				if line.startswith("1. "):
					start = True
					topic = line.strip().split(" ",1)[1]
					id_to_stances[str(file_index) + "_" + "1."] = "pro"
					id_to_text[str(file_index) + "_" + "1."] = topic
					sents_map[topic.lower()] = {"id":str(file_index) + "_" + "1.", "text_upper":topic, "stance":"pro", "responses":[]}
					sents_lower_pro.append(topic.lower())
					continue
				if start and line.strip() != "":
					parts = line.strip().split(" ",2)
					if len(parts) < 3:
						continue
					text = parts[2]
					_id = str(file_index) + "_" + parts[0]

					if text.lower().startswith("-> see 1"):
						ref = text.split()[-1]
						text = id_to_text[str(file_index) + "_" + ref]
						parent_id  = ".".join(_id.split(".")[:-2]) + "."
						parent_text = id_to_text[parent_id]
						sents_map[parent_text.lower()]["responses"].append(text)
						continue

					id_to_text[_id] = text
						
					parent_id  = ".".join(_id.split(".")[:-2]) + "."
					stance = parts[1].lower()[:-1]
					parent_stance = id_to_stances[parent_id]
					parent_text = id_to_text[parent_id]
					_stance = "pro"
					if parent_stance == stance:
						sents_lower_pro.append(text.lower())
						id_to_stances[_id] = "pro"
					else:
						sents_lower_con.append(text.lower())
						id_to_stances[_id] = "con"
						_stance = "con"

					sents_map[text.lower()] = {"id":_id, "text_upper":text, "stance":_stance, "responses":[]}
					sents_map[parent_text.lower()]["responses"].append(text)

	#following https://www.sbert.net/
	from sentence_transformers import SentenceTransformer
	model_name = 'paraphrase-distilroberta-base-v1' #'stsb-roberta-base' 'msmarco-distilbert-base-v3'
	model = SentenceTransformer(model_name)

	embeddings_pro = model.encode(sents_lower_pro)
	embeddings_con = model.encode(sents_lower_con)
	# sent_emb_dict =  dict(zip(sents, embeddings))

	sent_emb_dict_pro =  dict(zip(sents_lower_pro, embeddings_pro))
	sent_emb_dict_con =  dict(zip(sents_lower_con, embeddings_con))

	with open(sbert_path_pro_original, 'wb') as f:
 		cPickle.dump(sent_emb_dict_pro, f, cPickle.HIGHEST_PROTOCOL)
	with open(sbert_path_con_original, 'wb') as f:
		cPickle.dump(sent_emb_dict_con, f, cPickle.HIGHEST_PROTOCOL)       

	return embeddings_pro, embeddings_con, sents_lower_pro, sents_lower_con, sents_map



def index_vecs(embeddings_pro, embeddings_con, sbert_path_pro, sbert_path_con, sbert_path_all):
	n_pro = len(embeddings_pro) #number of vecs
	n_con = len(embeddings_con) #number of vecs
	n_all = n_pro + n_con
	d = len(embeddings_pro[0]) #dim of vecs

	# embeddings_all = embeddings_pro
	embeddings_all = np.concatenate([embeddings_pro, embeddings_con])

	#normalise vecs
	embeddings_pro /= np.linalg.norm(embeddings_pro, axis=1, keepdims=True)
	embeddings_con /= np.linalg.norm(embeddings_con, axis=1, keepdims=True)
	embeddings_all /= np.linalg.norm(embeddings_all, axis=1, keepdims=True)

	# embeddings_pro = normalize(embeddings_pro)
	# embeddings_con = normalize(embeddings_con)
	# embeddings_all = normalize(embeddings_all)

	

	#faiss indexing
	# index = faiss.IndexFlatIP(d)
	index_pro = faiss.IndexIDMap2(faiss.IndexFlatIP(d))
	index_pro.add_with_ids(embeddings_pro, np.array(range(0, n_pro)))

	index_con = faiss.IndexIDMap2(faiss.IndexFlatIP(d))
	index_con.add_with_ids(embeddings_con, np.array(range(0, n_con)))

	index_all = faiss.IndexIDMap2(faiss.IndexFlatIP(d))
	index_all.add_with_ids(embeddings_all, np.array(range(0, n_all)))

	faiss.write_index(index_pro, sbert_path_pro)
	faiss.write_index(index_con, sbert_path_con)
	faiss.write_index(index_all, sbert_path_all)

	# index.add(vectors)

	#save keys
	# with open(output_path, 'wb') as f:
	# 	cPickle.dump(vectors, f, cPickle.HIGHEST_PROTOCOL)

def search(index, query, sents, num_responses):
	# index = faiss.read_index(index_file)

	distances, indices = index.search(np.array([query]), num_responses)
	
	return distances.tolist()[0], [sents[_id] for _id in indices.tolist()[0]]
	              
def load_index(index_file):
	index = faiss.read_index(index_file)
	return index

if __name__ == "__main__":
	data_path = []
	_id = "veganism"
	config_path = "kialo_config.json"
	data_path_pro, data_path_con, data_path_all = "", "", ""
	sbert_path_pro, sbert_path_con, sbert_path_all, sbert_path_pro_original, sbert_path_con_original = "", "", "", "", ""

	with open(config_path) as f:
		config = json.load(f)
		for c in config["topics"]:
			if _id == c["id"]:
				data_path_pro = c["data_path_pro"]
				data_path_con = c["data_path_con"]
				data_path_all = c["data_path_all"]
				sbert_path_pro = c["sbert_path_pro"]
				sbert_path_con = c["sbert_path_con"]
				sbert_path_pro_original = c["sbert_path_pro_original"]
				sbert_path_con_original = c["sbert_path_con_original"]
				sbert_path_all = c["sbert_path_all"]
				datasets = c["datasets"]
				for d in datasets:
					data_path.append(d["data_path"])
	embeddings_pro, embeddings_con, sents_lower_pro, sents_lower_con, sents_map = parse_bert(data_path, sbert_path_pro_original, sbert_path_con_original)
	# file_path = "/Users/youmna/Documents/OUM2021/chat_app/server/python/kialoData/sbert/sbert_vecs_parent_license.pkl"
	# output_path = "/Users/youmna/Documents/OUM2021/chat_app/server/python/kialoData/sbert/sbert_vecs_parent_license_indexed"
	# f = open(file_path,'rb')
	# dict_vecs = cPickle.load(f)
	# vectors = []
	# keys = []
	# for k in dict_vecs:
	# 	vectors.append(dict_vecs[k])
	# 	keys.append(k)
	# f.close()
	fw_pro = open(data_path_pro, "w")
	fw_con = open(data_path_con, "w")
	fw_all = open(data_path_all, "w")

	for sent in sents_lower_pro:
		fw_pro.write(sent + "\t" + sents_map[sent]["id"] + "\t" + sents_map[sent]["text_upper"] + "\t" + sents_map[sent]["stance"] + "\t" + "\t".join(sents_map[sent]["responses"]) + "\n")
		fw_all.write(sent + "\t" + sents_map[sent]["id"] + "\t" + sents_map[sent]["text_upper"] + "\t" + sents_map[sent]["stance"] + "\t" + "\t".join(sents_map[sent]["responses"]) + "\n")
	for sent in sents_lower_con:
		fw_con.write(sent + "\t" + sents_map[sent]["id"] + "\t" + sents_map[sent]["text_upper"] + "\t" + sents_map[sent]["stance"] + "\t" + "\t".join(sents_map[sent]["responses"]) + "\n")
		fw_all.write(sent + "\t" + sents_map[sent]["id"] + "\t" + sents_map[sent]["text_upper"] + "\t" + sents_map[sent]["stance"] + "\t" + "\t".join(sents_map[sent]["responses"]) + "\n")

	index_vecs(embeddings_pro, embeddings_con, sbert_path_pro, sbert_path_con, sbert_path_all)

