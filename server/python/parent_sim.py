import numpy as np
import faiss 
from six.moves import cPickle
import re
import json
from sklearn.preprocessing import normalize

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
