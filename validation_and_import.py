#!/bin/env python

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import cerberus
import schema


OSM_PATH = "cardiff.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


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

def audit_street_type_simplified(street_name):
	search_result = street_type_re.search(street_name)
	if search_result is not None:
		search_type = search_result.group().title()
		if search_type not in expected:
			street_name = update_name(street_name, mapping)
			search_result = street_type_re.search(street_name)
			search_type = search_result.group().title()
			if search_type not in expected:
				return street_name
		return street_name

		

def shape_attrib(tag, id):
	one_tag = {}
	one_tag['id'] = id
	for attrib in tag.attrib:
		if attrib == "k":
			key = tag.attrib[attrib]
			if PROBLEMCHARS.match(key) is not None:
				break
			if LOWER_COLON.match(key) is not None:
				key_and_type = key.split(":", 1)
				one_tag['type'] = key_and_type[0]
				one_tag['key'] = key_and_type[1]
			else:
				one_tag['key'] = key
				one_tag['type'] = "regular"
		elif attrib == "v":
			if key == "addr:street":
				street_name = tag.attrib['v'].split(",")[0].title().replace("'S", "'s").strip()
				one_tag['value'] = audit_street_type_simplified(street_name)
			else:
				one_tag['value'] = tag.attrib[attrib]
	return one_tag


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
				  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
	"""Clean and shape 'node' or 'way' XML element to Python dict"""

	node_attribs = {}
	way_attribs = {}
	way_nodes = []
	tags = []  # Handle secondary tags the same way for both node and way elements
	
	if element.tag == 'node':
		id = ""
		for key in element.attrib.keys():
			if key in NODE_FIELDS:
				node_attribs[key] = element.attrib[key]
			if key == "id":
				id = element.attrib[key]
		for tag in element.iter("tag"):
			one_tag = shape_attrib(tag, id)
			tags.append(one_tag)
		return {'node': node_attribs, 'node_tags': tags}

	elif element.tag == 'way':
		id = ""
		for key in element.attrib.keys():
			if key in WAY_FIELDS:
				way_attribs[key] = element.attrib[key]
			if key == "id":
				id = element.attrib[key]
			
		for tag in element.iter("tag"):
			one_tag = shape_attrib(tag, id)
			tags.append(one_tag)
		
		count = 0     
		for tag in element.iter("nd"):
			one_tag={}
			one_tag['id'] = id
			one_tag['node_id'] = tag.attrib['ref']
			one_tag['position'] = count
			count += 1
			way_nodes.append(one_tag)
		
		return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}



def get_element(osm_file, tags=('node', 'way', 'relation')):
	"""Yield element if it is the right type of tag"""

	context = ET.iterparse(osm_file, events=('start', 'end'))
	_, root = next(context)
	for event, elem in context:
		if event == 'end' and elem.tag in tags:
			yield elem
			root.clear()


def validate_element(element, validator, schema=SCHEMA):
	"""Raise ValidationError if element does not match schema"""
	if validator.validate(element, schema) is not True:
		field, errors = next(validator.errors.iteritems())
		message_string = "\nElement of type '{0}' has the following errors:\n{1}"
		error_string = pprint.pformat(errors)
		
		raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
	"""Extend csv.DictWriter to handle Unicode input"""

	def writerow(self, row):
		super(UnicodeDictWriter, self).writerow({
			k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
		})

	def writerows(self, rows):
		for row in rows:
			self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
	"""Iteratively process each XML element and write to csv(s)"""


	with codecs.open(NODES_PATH, 'w') as nodes_file, \
		 codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
		 codecs.open(WAYS_PATH, 'w') as ways_file, \
		 codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
		 codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

		nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
		node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
		ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
		way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
		way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

		nodes_writer.writeheader()
		node_tags_writer.writeheader()
		ways_writer.writeheader()
		way_nodes_writer.writeheader()
		way_tags_writer.writeheader()
		
		validator = cerberus.Validator()
		
#		count = 0
		for element in get_element(file_in, tags=('node', 'way')):
#			if count > 1000:
#				break
#			count += 1 
			el = shape_element(element)
			if el:
				if validate is True:
					validate_element(el, validator)
				else:
					pprint.pprint(el)

				if element.tag == 'node':
					nodes_writer.writerow(el['node'])
					node_tags_writer.writerows(el['node_tags'])
				elif element.tag == 'way':
					ways_writer.writerow(el['way'])
					way_nodes_writer.writerows(el['way_nodes'])
					way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
	# Note: Validation is ~ 10X slower. For the project consider using a small
	# sample of the map when validating.
	process_map(OSM_PATH, validate=True)