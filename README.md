# chat-app
This is a chat application between the wizard of oz and a participant! This project is based on the GitHub project https://github.com/jherr/chat-o-matic

Before running the code, install the dependecies by running the following command in the folders: server, client, woz and participant:
```sh
yarn install
```
You can also install python dependecies by running:
```sh
pip install server/python/requirements.txt
```
To run the project, execute the following in the folders: server, client, woz and participant:  
```sh
yarn start
```
The wizard of oz client will be running on http://localhost:8082/ and the participant client will be running on http://localhost:8081/ 

You can use the TF-IDF model in the wizard page to retrieve the responses that are most similar to the user's last utterance. In order to use Google's word2vec or GloVe pre-trained models, download [
GoogleNews-vectors-negative300.bin.gz](https://drive.google.com/file/d/0B7XkCwpI5KDYNlNUTTlSS21pQmM/edit) or [glove.840B.300d.zip](https://nlp.stanford.edu/projects/glove/) and save in server/python/embeddings. 
