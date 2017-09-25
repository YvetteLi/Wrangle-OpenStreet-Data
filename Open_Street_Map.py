import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import sqlite3
import pprint


## The script first reads the file and collect a set of all the distinct tags
## Due to the size of the file, the program will read in first 20000 lines of the entries



def get_distinct_top_tag(file_name):
	with open(file_name, "r") as file:
		distinct_tag = set()
		count = 0
		for event, elem in ET.iterparse(file, events = ("start", )):
			print (elem.attrib)

			# get distinct top tags
			distinct_tag.add(elem.tag)
		return distinct_tag


street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
street_types = defaultdict(set)

expected = ["Lane", "Avenue", "Drive", "Street", "Court", "Quay", "Centre", "Corner", "Yard", "Way", "Terrace", "Place", "Park", "Crescent", "Close", "Arcade", "Walk", "Square", "Quarter", "Mews", "Kingsway", "Grove", "Approach","View", "Gardens", "Road", "East", "West", "North", "South"]

mapping = { "Garden": "Gardens",
		"Cresent": "Crescent",
		"Pierheadstreet": "Pierhead Street",
		"W" : "West",
		"Rd" : "Road"}
		
def update_name(name, mapping):
	for target in mapping:
		if target in name:
			return name.replace(target, mapping[target])
	return name

def audit_street_type(street_types, street_name):
	search_result = street_type_re.search(street_name)
	if search_result is not None:
		search_type = search_result.group().title()
		if search_type not in expected:
			street_name = update_name(street_name, mapping)
			search_result = street_type_re.search(street_name)
			search_type = search_result.group().title()
			if search_type not in expected:
				street_types[search_type].add(street_name)
		else: 
			street_types[search_type].add(street_name)

def is_street_name(elem):
	return (elem.tag == "tag") and (elem.attrib['k']) == "addr:street"

def audit(osmfile):
	with open(osmfile, "r") as osm_file:	
		for event, elem in ET.iterparse(osm_file, events = ("start", )):			
			if elem.tag == "way" or elem.tag == "node":
				for tag in elem.iter("tag"):
					if is_street_name(tag):
						street_name = tag.attrib['v'].split(",")[0].title().replace("'S", "'s")
						audit_street_type(street_types, street_name)           
		return street_types



file_name = "cardiff.osm"
#	distinct_tag = get_distinct_top_tag(file_name)
result_dict = (audit(file_name))

pprint.pprint (result_dict)




