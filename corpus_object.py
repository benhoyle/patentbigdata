import os
import logging
import re

#Libraries for Zip file processing
import zipfile
from zip_open import zopen
import cStringIO

#Library for XML Parsing
from xml.dom.minidom import parseString

#test_path= "/media/SAMSUNG/Patent Downloads/2001"

class MyCorpus():
	#Creates a new corpus object that simplifies processing of patent archive
	def __init__(self, path="/media/SAMSUNG/Patent Downloads"):
		logging.basicConfig(filename="processing_class.log", format='%(asctime)s %(message)s')
		self.exten = ".zip"
		self.path = path
		#Set regular expression for valid patent publication files
		self.FILE_FORMAT_RE = re.compile(r".+US\d+[A,B].+-\d+\.\w+")
		#Set a list of upper level zip files in the path
		self.first_level_files = [os.path.join(subdir,f) for (subdir, dirs, files) in os.walk(self.path) for f in files if f.lower().endswith(".zip")]
		#Initialise arrays for lower level files
		self.processed_fl_files = []
		self.zip_file_list = []

	def get_zip_list(self):
		#Class function to generate a list of lower level zip files
		for filename in self.first_level_files:
			try:
				#Look to see if we have already processed
				if filename not in self.processed_fl_files:
					zfl = [(filename, name) for name in zipfile.ZipFile(filename, "r").namelist() if name.lower().endswith(self.exten) and self.FILE_FORMAT_RE.match(name)]
					self.zip_file_list += zfl
					self.processed_fl_files.append(filename)
		
			except Exception, ex:
				#Log error
				logging.exception("Exception opening file:" + str(filename))

	def read_xml(self, zip_file_index):
		#Functions reads XML from a particular zip file (second_level_zip_file)
		#that is nested within a first zip file (first_level_zip_file)
		#Takes an index to a file within the zip_file_list array
		first_level_zip_file, second_level_zip_file = self.zip_file_list[zip_file_index]
		file_name_section = second_level_zip_file.rsplit('/',1)[1].split('.')[0]
		XML_path = file_name_section + '/' + file_name_section + ".XML"
		print XML_path
		with zipfile.ZipFile(first_level_zip_file) as z:
			with z.open(second_level_zip_file) as z2:
				z2_filedata = cStringIO.StringIO(z2.read())
				with zipfile.ZipFile(z2_filedata) as nested_zip:
					filename_end = XML_path.rsplit('/', 1)[1]
					with nested_zip.open(XML_path) as xml_file:
						xml_tree = parseString(xml_file.read())
		#Return minidom DOM object
		return xml_tree


 



