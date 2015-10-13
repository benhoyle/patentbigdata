import os
import logging
import re
import math

#Libraries for Zip file processing
import zipfile
import tarfile
from zip_open import zopen
import cStringIO

#Library for XML Parsing
from xml.dom.minidom import parseString

#Library for text analysis
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.probability import FreqDist
from nltk import stem
from nltk.corpus import stopwords

#test_path= "/media/SAMSUNG/Patent_Downloads/2001"

class MyCorpus():
	#Creates a new corpus object that simplifies processing of patent archive
	def __init__(self, path="/media/SAMSUNG/Patent_Downloads"):
		logging.basicConfig(filename="processing_class.log", format='%(asctime)s %(message)s')
		self.exten = (".zip",".tar")
		self.path = path
		#Set regular expression for valid patent publication files
		self.FILE_FORMAT_RE = re.compile(r".+US\d+[A,B].+-\d+\.\w+")
		#Set a list of upper level zip files in the path
		self.first_level_files = [os.path.join(subdir,f) for (subdir, dirs, files) in os.walk(self.path) for f in files if f.lower().endswith(self.exten)]
		#Initialise arrays for lower level files
		self.processed_fl_files = []
		self.archive_file_list = []
		
		#Set English stopwords
		self.stopwords = stopwords.words('english')

	def get_archive_list(self):
		#Class function to generate a list of lower level archive files
		for filename in self.first_level_files:
			if filename.lower().endswith(".zip"):
				try:
					#Look to see if we have already processed
					if filename not in self.processed_fl_files:
						afl = [(filename, name) for name in zipfile.ZipFile(filename, "r").namelist() if name.lower().endswith(self.exten) and self.FILE_FORMAT_RE.match(name)]
						self.archive_file_list += afl
						self.processed_fl_files.append(filename)
				except Exception, ex:
					#Log error
					logging.exception("Exception opening file:" + str(filename))
			elif filename.lower().endswith(".tar"):
				try:
					#Look to see if we have already processed
					if filename not in self.processed_fl_files:
						#There is no namelist() function in TarFile
						current_file = tarfile.TarFile(filename, "r")
						names = current_file.getnames()
						current_file.close()
						afl = [(filename, name) for name in names if name.lower().endswith(self.exten) and self.FILE_FORMAT_RE.match(name)]
						self.archive_file_list += afl
						self.processed_fl_files.append(filename)
				except Exception, ex:
					#Log error
					logging.exception("Exception opening file:" + str(filename))

	def read_xml(self, a_file_index):
		#Functions reads XML from a particular zip file (second_level_zip_file)
		#that is nested within a first zip file (first_level_zip_file)
		#Takes an index to a file within the zip_file_list array
		first_level_a_file, second_level_a_file = self.archive_file_list[a_file_index]
		file_name_section = second_level_a_file.rsplit('/',1)[1].split('.')[0]
		XML_path = file_name_section + '/' + file_name_section + ".XML"
		if first_level_a_file.lower().endswith(".zip"):
			with zipfile.ZipFile(first_level_a_file) as z:
				with z.open(second_level_a_file) as z2:
					z2_filedata = cStringIO.StringIO(z2.read())
					#if second_level_a_file.endswith(".zip"): - add here second check for second level tar files
					with zipfile.ZipFile(z2_filedata) as nested_zip:
						with nested_zip.open(XML_path) as xml_file:
							xml_tree = parseString(xml_file.read())
					#elif second_level_a_file.endswith(".tar"): -to add
		elif first_level_a_file.lower().endswith(".tar"):
			with tarfile.TarFile(first_level_a_file) as z:
				z2 = z.extractfile(second_level_a_file)
				#z2_filedata = cStringIO.StringIO(z2.read())
				with zipfile.ZipFile(z2) as nested_zip:
					with nested_zip.open(XML_path) as xml_file:
						xml_tree = parseString(xml_file.read())
		return xml_tree

	def __get_text(self, elem, string=""):
		#Recursive function used to get text from XML DOM
		#Check if element has a text node
		if elem.hasChildNodes():
			for child in elem.childNodes:
				if child.nodeName == '#text':
					string = string + child.nodeValue
				else:
					string = self.__get_text(child, string)		
		return string

	def extract_text(self, xml_tree):
		#Function to extract text from an XML DOM object
		text_string = ""
		for elem in xml_tree.getElementsByTagName("title-of-invention"):
			out_str = self.__get_text(elem)
			text_string = text_string + out_str + "\n"
		for elem in xml_tree.getElementsByTagName("paragraph"):
			out_str = self.__get_text(elem)
			text_string = text_string + out_str + "\n"
		for elem in xml_tree.getElementsByTagName("claim"):
			out_str = self.__get_text(elem)
			text_string = text_string + out_str + "\n"
		return text_string

#Should the word processing functions below go in a separate module?
	def __get_words(self, text_string):
		#Tokenize text into words / punctuation and
		#clean words to remove punctuation and english stopwords / place in lower case
		clean_words = [w.lower() for w in word_tokenize(text_string) if w.isalpha() and w.lower() not in self.stopwords]
		return clean_words

	def __freq(self, word, doc):
	    return doc.count(word)
	
	def __word_count(self, doc):
	    return len(doc)
	
	def __tf(self, word, doc):
	    return (self.__freq(word, doc) / float(self.__word_count(doc)))
	
	def __num_docs_containing(self, word, list_of_docs):
	    count = 0
	    for document in list_of_docs:
	        if self.__freq(word, document) > 0:
	            count += 1
	    return 1 + count
	
	def __idf(self, word, list_of_docs):
	    return math.log(len(list_of_docs) /
	            float(self.__num_docs_containing(word, list_of_docs)))
	
	def __tf_idf(self, word, doc, list_of_docs):
	    return (self.__tf(word, doc) * self.__idf(word, list_of_docs))

	def get_tf_idf(self, documents):
		#Function to calculate TF-IDF given a set of documents
		#'documents' is an array of indexes
		doc_results = {}
		vocabulary = []
		#Iterate through documents
		for doc_index in documents:
			tokens = self.__get_words(self.extract_text(self.read_xml(doc_index)))
			final_tokens = tokens #final_tokens may change if adding bi/tri-grams
			
			#Initialise dictionary to store results
			doc_results[doc_index] = {'freq': {}, 'tf': {}, 'idf': {},
			 'tf-idf': {}, 'tokens': []}
                        
			for token in final_tokens:
				#The frequency computed for each document
				doc_results[doc_index]['freq'][token] = self.__freq(token, final_tokens)
				#The term-frequency (Normalized Frequency)
				doc_results[doc_index]['tf'][token] = self.__tf(token, final_tokens)
				doc_results[doc_index]['tokens'] = final_tokens
		
			vocabulary.append(final_tokens)
		
		for doc_index in documents:
			for token in doc_results[doc_index]['tf']:
				#The Inverse-Document-Frequency
				doc_results[doc_index]['idf'][token] = self.__idf(token, vocabulary)
				#The tf-idf
				doc_results[doc_index]['tf-idf'][token] = self.__tf_idf(token, doc_results[doc_index]['tokens'], vocabulary)
		
		#Now let's find out the most relevant words by tf-idf.
		words = {}
		for doc_index in documents:
		    for token in doc_results[doc_index]['tf-idf']:
		        if token not in words:
		            words[token] = doc_results[doc_index]['tf-idf'][token]
		        else:
		            if doc_results[doc_index]['tf-idf'][token] > words[token]:
		                words[token] = doc_results[doc_index]['tf-idf'][token]
		
		    print doc_index
		    for token in doc_results[doc_index]['tf-idf']:
		        print token, doc_results[doc_index]['tf-idf'][token]
		
		for item in sorted(words.items(), key=lambda x: x[1], reverse=True):
		    print "%f <= %s" % (item[1], item[0])
		
		#porter = stem.porter.PorterStemmer()
		##stem here? - stemming using porter
		#vocab = [porter.stem(w.lower()) for w in words if w.isalpha()]
		
		##add to FreqDist here?
		#for stem_word in vocab:
			#f_dist.inc(stem_word)
			
		##Save state in picke file
		#with open("freqdist.pkl", "wb") as f:
			#pickle.dump(f_dist, f)

	#def save_string(self, text_string, text_filename):
		#with open(text_filename, 'w') as f:
			#f.write(text_string)

 



