from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from nltk.stem.porter import *
from nltk.tokenize import word_tokenize
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

unk_words = {}
vectors = {}

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
	for text in texts:
			vec = []
			words = word_tokenize(text)
			for w in words:
				if w in model:
					vec.append(model[w])
				elif w in unk_words:
					vec.append(unk_words[w])
				else:
					unk_rep = np.random.normal(0.0, 0.01, 300)
					unk_words[w] = unk_rep
					vec.append(unk_rep)
			sent_vec = np.array(vec).mean(axis=0)
			vectors[text] = sent_vec#.reshape(-1, )
	return vectors

def most_sim_cos(vectors, text, num_responses):
	most_similar = [""]
	max_sim = [-1]
	for t in vectors:
		if t == text:
			continue
		sim = cosine_similarity(np.array(vectors[text].reshape(1,-1)),np.array(vectors[t].reshape(1,-1)))[0][0]
		if len(max_sim) < num_responses or sim > max_sim[0]:
			most_similar.append(t)
			max_sim.append(sim)
			sorted_most_similar = [x for _,x in sorted(zip(max_sim,most_similar))]
			max_sim.sort()
			most_similar = sorted_most_similar
			if sim > max_sim[0]:
				max_sim  = max_sim[1:]
				most_similar = sorted_most_similar[1:]
	return most_similar

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
	sorted_most_similar = [x for _,x in sorted(zip(sim_array,prop_content_texts))]
	sim_array.sort()
	most_similar =  sorted_most_similar[-num_responses:]
	return most_similar