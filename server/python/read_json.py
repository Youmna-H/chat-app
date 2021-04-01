import json
import argparse
import os
import gensim
import utils
from nltk.tokenize import word_tokenize
from six.moves import cPickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# import nltk
# nltk.download('stopwords')
# from nltk.corpus import stopwords  
# stop_words = set(stopwords.words('english')) 
np.random.seed(123)
# Chair: Michael Buerk
# Panellists: Clifford Longley, Claire Fox, Michael Portillo and Matthew Taylor. 
# Witnesses: Nick Dearden, Simon Rose, John Lamiday and Jamie Whyte. 
utt_to_stance = {}
text_to_stance_lower = {}
topic = {"money": "Morality of Money:\tBut the crisis has reinforced the more old fashioned view, that taking on unaffordable debts, nationally or individually, is inherently wrong, and bankruptcy a matter of shame.  Either way, how do you strike a moral balance between the interests of the lender and the borrower? The morality of money and debt is our moral maze tonight",
"empire":"British Empire:\tIs it right to make moral judgments about the past through the prism of our modern sensibilities? Should we be held responsible for the sins of Empire and if so where should it stop? That's our Moral Maze tonight."
}
def load_json(path):
	data = json.load(path)

def read_data_from_file(file, node_type):
	nodes, edges, text_to_id = {}, {}, {}
	with open(file) as f:
		obj = json.load(f)
		obj["map"] = file
		map_name = file.split('/')[-1].split('.')[0].replace('nodeset','')
		for node in obj["nodes"]:
			if node['type'].lower() != node_type:
				continue
			node['map'] = map_name
			node['to_texts'] = []
			node['text'] = node['text'].strip() #cleanup
			node['stance'] = utt_to_stance[node['text'].strip()]
			text_to_stance_lower[node['text'].strip().lower()] = utt_to_stance[node['text'].strip()]
			nodes[node['nodeID']+'_'+map_name] = node #add +file in case id is duplicated across maps
			# if node['text'].lower() in text_to_id:
			# 	print(node['text'])
			text_to_id[node['text'].lower()] = node['nodeID']+'_'+map_name
		for edge in obj["edges"]:
			edges[edge['edgeID']+'_'+map_name] = edge

	return nodes, edges, text_to_id

#note that same nodes "nodeID" are repeated in different files, as they map to the same node
if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--dataset", dest="dataset", type=str, choices=["money", "empire"], required=False, default="money", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	# parser.add_argument("-p", "--data_path", dest="data_path", type=str, required=False, default="/Users/youmna/Documents/OUM2021/MoralMazeData/Money", help="The path to the data, could be one file or a directory") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-u", "--utt_type", dest="utt_type", choices=['i', 'l'], type=str, required=False, default="i", help="The type of utterance, i for propositions and l for locutions") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-m", "--sim_model", dest="sim_model", choices=['word2vec', 'glove', 'tfidf', 'sbert'], type=str, required=False, default="tfidf", help="The similarity model") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-q", "--query", dest="query", type=str, required=True, default="", help="User's query") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-n", "--num_responses", dest="num_responses", type=int, required=False, default=5, help="Number of similar responses to retrieve") #default is false in case of loading a pretrained model, and just testing on test set
	parser.add_argument("-rp", "--responses_per_stance", dest="responses_per_stance", choices = [0,1], type=int, required=False, default=1, help="Set to true if you want the number of responses to be per stance") #default is false in case of loading a pretrained model, and just testing on test set

	# parser.add_argument("-rs", "--remove_stop", dest="remove_stopwords", type=bool, required=False, default=False, help="Whether to remove stop words in similarity models") #default is false in case of loading a pretrained model, and just testing on test set

	# parser.add_argument("-m", "--sim_measure", dest="sim_measure", choices=['utterance', 'response'], type=str, required=False, default="utterance", help="return most similar sentence or most the response to the similar sentence") #default is false in case of loading a pretrained model, and just testing on test set
	pre_path = "python/"
	# pre_path = ""
	args = parser.parse_args()
	data_path = pre_path + 'MoralMazeData/Money'
	bert_path  =  pre_path  + 'MoralMazeData/sbert/sbert_vecs_money.pkl'
	# data_path = os.path.abspath('MoralMazeData/Money')
	utt_to_stance_path = pre_path + 'MoralMazeData/money_utt_stances.txt'
	if args.dataset == "empire":
		data_path = pre_path + 'MoralMazeData/britishempire'
		utt_to_stance_path = pre_path + 'MoralMazeData/british_empire_utt_stances.txt'
		bert_path  =  pre_path  + 'MoralMazeData/sbert/sbert_vecs_britishempire.pkl'

	with open(utt_to_stance_path) as f:
		for line in f:
			parts = line.strip().split('\t',2)
			utt_to_stance[parts[2]] = parts[1]

	# assert args.utt_type == "i" or args.utt_type == "l"
	ids = {}
	#check if provided path is a file or directory
	is_file = os.path.isfile(data_path) # Does bob.txt exist?  Is it a file, or a directory?
	nodes = {}
	edges = {}
	locutions = {}
	text_to_id = {}
	prop_content_texts = []
	prop_content_texts_pro = []
	prop_content_texts_con = []
	prop_content_texts_neutral = []
	ids = {}
	
	if is_file:
		nodes, edges, text_to_id = read_data_from_file(args.data_path, args.utt_type.lower())
	#read files in dir
	else:
		json_files = [os.path.join(data_path, f) for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f)) and f.endswith('.json')]
		for file in json_files:
			n, e, t = read_data_from_file(file, args.utt_type.lower())
			nodes.update(n)
			edges.update(e)
			text_to_id.update(t)

	for key in nodes:
		node = nodes[key]
		if node['type'].lower() == args.utt_type.lower():
			prop_content_texts.append(node['text'].lower())
			if node['stance'] == 'pro':
				prop_content_texts_pro.append(node['text'].lower())
			elif node['stance'] == 'con':
				prop_content_texts_con.append(node['text'].lower())
			else:
				prop_content_texts_neutral.append(node['text'].lower())

	for key in edges:
		edge = edges[key]
		node_id = edge['fromID']+'_'+key.split('_')[1]
		if node_id not in nodes:
			continue
		node = nodes[node_id]
		if node['type'].lower() != args.utt_type.lower():
			continue
		to_node_id = edge['toID']+'_'+key.split('_')[1]
		for key2 in edges:
			edge = edges[key2]
			if edge['fromID']+'_'+key2.split('_')[1] == to_node_id:
				to_node_id2 = edge['toID']+'_'+key2.split('_')[1]
				if to_node_id2 not in nodes:
					continue
				to_node = nodes[to_node_id2]
				if to_node['text'] == 'TA' or to_node['text'] == 'YA':
					node['to_texts'].append(to_node['text'].lower())
				else:
					node['to_texts'].insert(0,to_node['text'].lower())

	
	most_similar = []
	most_similar_pro = []
	most_similar_con = []
	most_similar_neutral = []
	max_sim = -1
	text = args.query.lower()
	# text = prop_content_texts[0]
	# text = "Are you a saver or a debtor?"
	# text = "It is better for people to spend money withing the limits of their capabilities"
	# text = "loans are useful for students for example to continue their education"
	# text = "what do you think of the british empire"
	prop_content_texts.append(text)
	prop_content_texts_pro.append(text)
	prop_content_texts_con.append(text)
	prop_content_texts_neutral.append(text)
	# print('Query: ')
	# print(text)
	# print('-------------')
	if args.sim_model == 'sbert':
		infile = open(bert_path,'rb')
		vectors_all = cPickle.load(infile)
		infile.close()
		if text not in vectors_all:
			vectors_all[text] = utils.get_sbert_vec(text)
		if args.responses_per_stance == 0:
			vectors = { d: vectors_all[d] for d in prop_content_texts }
			most_similar = utils.most_sim_cos(vectors, text, args.num_responses)
		else:
			vectors_pro = { d: vectors_all[d] for d in prop_content_texts_pro }
			most_similar_pro = utils.most_sim_cos(vectors_pro, text, args.num_responses)
			vectors_con = { d: vectors_all[d] for d in prop_content_texts_con }
			most_similar_con = utils.most_sim_cos(vectors_con, text, args.num_responses)
			vectors_neutral = { d: vectors_all[d] for d in prop_content_texts_neutral }
			most_similar_neutral = utils.most_sim_cos(vectors_neutral, text, args.num_responses)
	elif args.sim_model == 'word2vec':
		path = pre_path + "embeddings/GoogleNews-vectors-negative300.bin"
		model = gensim.models.KeyedVectors.load_word2vec_format(path, binary=True)
		
		if args.responses_per_stance == 0:
			vectors = utils.get_vectors(model, prop_content_texts)
			most_similar = utils.most_sim_cos(vectors, text, args.num_responses)
		else:
			vectors_pro = utils.get_vectors(model, prop_content_texts_pro)
			most_similar_pro = utils.most_sim_cos(vectors_pro, text, args.num_responses)
			vectors_con = utils.get_vectors(model, prop_content_texts_con)
			most_similar_con = utils.most_sim_cos(vectors_con, text, args.num_responses)
			vectors_neutral = utils.get_vectors(model, prop_content_texts_neutral)
			most_similar_neutral = utils.most_sim_cos(vectors_neutral, text, args.num_responses)
	elif args.sim_model == 'glove':
		path = pre_path + "embeddings/glove.840B.300dword2vec.txt"
		# path = '/Users/youmna/Documents/Phd_year2/Coherence_acl/GC_wsj/glove.6B.100d.word2vec.txt'
		model = utils.read_emb_text(path)
		if args.responses_per_stance == 0:
			vectors = utils.get_vectors(model, prop_content_texts)
			most_similar = utils.most_sim_cos(vectors, text, args.num_responses)
		else:
			vectors_pro = utils.get_vectors(model, prop_content_texts_pro)
			most_similar_pro = utils.most_sim_cos(vectors_pro, text, args.num_responses)
			vectors_con = utils.get_vectors(model, prop_content_texts_con)
			most_similar_con = utils.most_sim_cos(vectors_con, text, args.num_responses)
			vectors_neutral = utils.get_vectors(model, prop_content_texts_neutral)
			most_similar_neutral = utils.most_sim_cos(vectors_neutral, text, args.num_responses)
	elif args.sim_model == 'tfidf':
		# from scipy import spatial
		# stemmer = PorterStemmer()
		# def stemmed_words(doc):
		# 	return (stemmer.stem(w) for w in analyzer(doc))
		# # vect = TfidfVectorizer(min_df=1, stop_words="english")  
		# # create the transform
		# analyzer = TfidfVectorizer().build_analyzer()
		
		if args.responses_per_stance == 0:
			most_similar = utils.get_tfidf_sim(prop_content_texts, args.num_responses, text)
		else:
			most_similar_pro = utils.get_tfidf_sim(prop_content_texts_pro, args.num_responses, text)
			most_similar_con = utils.get_tfidf_sim(prop_content_texts_con, args.num_responses, text)
			most_similar_neutral = utils.get_tfidf_sim(prop_content_texts_neutral, args.num_responses, text)
		# for i, sim in enumerate(sim_array): #score between i and j 
		# 	if i == index or prop_content_texts[i] == text:
		# 		continue
		# 	if sim > max_sim:
		# 		max_sim = sim
		# 		most_similar = prop_content_texts[i]
	if args.responses_per_stance == 0:
		most_similar.reverse()
		_id = [text_to_id[i] for i in most_similar]
		stances = [text_to_stance_lower[i] for i in most_similar]
		# print(_id)
		# print('most similar sentence to query:  ')
		print("###///".join(most_similar) + "$!$!$" + "###///".join(stances))
		# print('----------------')
		# print("Responses to the most similar sentence to query (including all types of transitions):")
		# print(nodes[_id]['to_texts'])
	else:
		most_similar_pro.reverse()
		most_similar_con.reverse()
		most_similar_neutral.reverse()
		print( "###///".join(most_similar_pro) + "$!$!$" + "###///".join(most_similar_con)+ "$!$!$" + "###///".join(most_similar_neutral))

