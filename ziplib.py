import os
#Libraries for Zip file processing
import zipfile
from zip_open import zopen
import cStringIO

import logging
import re

#Library for XML Parsing
from xml.dom.minidom import parseString

logging.basicConfig(filename="processing.log", format='%(asctime)s %(message)s')

archive_path = "/media/SAMSUNG/Patent Downloads/2001"
FILE_FORMAT_RE = re.compile(r".+US\d+[A,B].+-\d+\.\w+")

#>>>>>>>>>>>>>>>>>>>>>>>
#Text processing functions below should be in separate file

def get_text(elem, string=""):
	#Check if element has a text node
	if elem.hasChildNodes():
		for child in elem.childNodes:
			if child.nodeName == '#text':
				string = string + child.nodeValue
			else:
				string = get_text(child, string)		
	return string
	
def extract_text(xml_tree):
	text_string = ""
	
	for elem in xml_tree.getElementsByTagName("title-of-invention"):
		out_str = get_text(elem)
		text_string = text_string + out_str + "\n"
							
	for elem in xml_tree.getElementsByTagName("paragraph"):
		out_str = get_text(elem)
		text_string = text_string + out_str + "\n"
							
	for elem in xml_tree.getElementsByTagName("claim"):
		out_str = get_text(elem)
		text_string = text_string + out_str + "\n"
		
	return text_string
	
def save_string(text_string, text_filename):
	with open(text_filename, 'w') as f:
		f.write(text_string)

#Functions above should be in separate file
#>>>>>>>>>>>>>>>>>>>>>

#Patent Archive Processing Functions

def step(arg, dirname, names):
	#Function steps through zip files
	exten = '.zip'
	exten = exten.lower()
	for name in names:
		if name.lower().endswith(exten):
			
			process_zip(str(os.path.join(dirname, name)))

def process_zip(filename):
	#Processing a patent publication archive
	exten = '.zip'
	first_level_zip_file = filename
	i = 0
	try:
		zip_file = zipfile.ZipFile(filename, "r")
	
		for name in zip_file.namelist():
			#filter these for files ending in ZIP
			if name.lower().endswith(exten):
						
				second_level_zip_file = name
				
				#Need to use regular expressions to avoid anything not an A or B publication
				if FILE_FORMAT_RE.match(name):
					print i
					i = i + 1
					read_xml(first_level_zip_file, second_level_zip_file)

	except Exception, ex:
		#Log error
		logging.exception("Exception opening file:" + str(filename))
		return

def read_xml(first_level_zip_file, second_level_zip_file):
	#Functions reads XML from a particular zip file (second_level_zip_file)
	#that is nested within a first zip file (first_level_zip_file)
	file_name_section = second_level_zip_file.rsplit('/',1)[1].split('.')[0]
	XML_path = file_name_section + '/' + file_name_section + ".XML"
	
	with zipfile.ZipFile(first_level_zip_file) as z:
		with z.open(second_level_zip_file) as z2:
			z2_filedata = cStringIO.StringIO(z2.read())
			with zipfile.ZipFile(z2_filedata) as nested_zip:
				
				filename_end = XML_path.rsplit('/', 1)[1]
				#text_filename = CORPUS_PATH + filename_end.split('.')[0] + ".TXT" 
				print XML_path
				#with nested_zip.open(XML_path) as xml_file:
					#xml_tree = parseString(xml_file.read())
					#logging.error("Opening: " + XML_path)
					#text_string = extract_text(xml_tree) #Extracting string from XML data
					#Process on text_String
					
			z2_filedata.close()
 

 
# Start the walk

os.path.walk(archive_path, step, "")
