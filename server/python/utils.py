# from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
# from nltk.stem.porter import *
# from nltk.tokenize import word_tokenize
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

unk_words = {}
vectors = {}

def get_sbert_model(sbert_model_name='paraphrase-distilroberta-base-v1'):
	#get sbert vec https://www.sbert.net/
	from sentence_transformers import SentenceTransformer
	model = SentenceTransformer(sbert_model_name) #('msmarco-distilbert-base-v3')
	return model 

def get_sbert_vec(model, text):
	return model.encode(text)

def get_sbert_mostsimilar_crossencoder(vecs, query, query_vec, num_responses):
	distances, most_similar = most_sim_cos(vecs, query_vec, 50)
	from sentence_transformers import CrossEncoder
	model = CrossEncoder('cross-encoder/stsb-roberta-base')
	cross_inp = [[query, i] for i in most_similar]
	cross_scores = model.predict(cross_inp)

	cross_scores, most_similar = zip(*sorted(zip(cross_scores, most_similar), reverse=True))

	return list(cross_scores[:num_responses]), list(most_similar[:num_responses])

# def rerank():

def read_emb_text(emb_path):
	embeddings = {}
	with open(emb_path, 'r') as f:
		for line in f:
			values = line.split()
			word = values[0]
			try:
				coefs = np.asarray(values[1:], dtype=np.float)#.astype(np.float)
			except:
				continue
			coefs = np.asarray(values[1:], dtype=np.float)#.astype(np.float)
			embeddings[word] = coefs
	f.close()
	return embeddings

def get_vectors(model, texts):
	vectors = {}
	unk_rep = np.random.normal(0.0, 0.01, 300)
	model['$UNK'] = unk_rep
	for text in texts:
		vec = []
		sent_vec = get_vector(model, text, unk_rep)
		vectors[text] = sent_vec
		# vectors.append(sent_vec)
	return vectors, model

def get_vector(model, text, unk_rep=[]):
	vec = []
	words = word_tokenize(text)
	for w in words:
		if w in model:
			vec.append(model[w])
		else:
			if unk_rep == []:
				unk_rep = model['$UNK']
			vec.append(unk_rep)
	sent_vec = np.array(vec).mean(axis=0)
	return sent_vec

def most_sim_cos_with_vecs(vectors, query_vec, num_responses=100):
	most_similar = [""]
	most_vecs = []
	max_sim = [-1]
	query_vec = np.array(query_vec.reshape(1,-1))
	for t in vectors:
		vec = np.array(vectors[t].reshape(1,-1))
		sim = cosine_similarity(query_vec, vec)[0][0]
		if len(max_sim) < num_responses or sim > max_sim[0]:
			most_similar.append(t)
			max_sim.append(sim)
			most_vecs.append(vec)
			max_sim, most_similar, most_vecs = zip(*sorted(zip(max_sim, most_similar, most_vecs)))
			max_sim = list(max_sim)
			most_similar = list(most_similar)
			most_vecs = list(most_vecs)
			if len(max_sim) > num_responses:
				max_sim  = max_sim[1:]
				most_similar = most_similar[1:]
				most_vecs = most_vecs[1:]
	most_similar.reverse()
	max_sim.reverse()
	most_vecs.reverse()
	return max_sim, most_similar, most_vecs

def most_sim_cos(vectors, query_vec, stances, num_responses):
	most_similar = [""]
	max_sim = [-1]
	sim_stances = []
	query_vec = np.array(query_vec.reshape(1,-1))
	for t in vectors:
		vec = np.array(vectors[t].reshape(1,-1))
		sim = cosine_similarity(query_vec, vec)[0][0]
		stance = stances[t]
		if len(max_sim) < num_responses or sim > max_sim[0]:
			most_similar.append(t)
			max_sim.append(sim)
			sim_stances.append(stance)
			max_sim, most_similar, sim_stances = zip(*sorted(zip(max_sim, most_similar, sim_stances)))
			max_sim = list(max_sim)
			most_similar = list(most_similar)
			sim_stances = list(sim_stances)
			# sorted_most_similar = [x for _,x in sorted(zip(max_sim,most_similar))]
			# max_sim.sort()
			# most_similar = sorted_most_similar
			if len(max_sim) > num_responses:
				max_sim  = max_sim[1:]
				most_similar = most_similar[1:]
				sim_stances = sim_stances[1:]
	most_similar.reverse()
	max_sim.reverse()
	sim_stances.reverse()
	return max_sim, most_similar, sim_stances

def get_tfidf_sim(prop_content_texts, num_responses, text):
	vectorizer = TfidfVectorizer(stop_words="english")
	tfidf = vectorizer.fit_transform(prop_content_texts)
	pairwise_similarity = tfidf * tfidf.T 
	#get index of sentence
	index = prop_content_texts.index(text)
	sim_array = pairwise_similarity.toarray()[index]
	#remove exact text
	sim_array_modified = []
	prop_content_texts_modified =  []
	for i, sim in enumerate(sim_array):
		if prop_content_texts[i] != text:
			sim_array_modified.append(sim)
			prop_content_texts_modified.append(prop_content_texts[i])
	sim_array = sim_array_modified
	prop_content_texts =  prop_content_texts_modified
	# sim_array, most_similar = zip(*sorted(zip(sim_array, prop_content_texts)))
	sorted_most_similar = [x for _,x in sorted(zip(sim_array,prop_content_texts))]
	sim_array.sort()
	most_similar =  sorted_most_similar[-num_responses:]
	most_similar.reverse()
	sim_array.reverse()
	return sim_array, most_similar