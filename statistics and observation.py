#!/usr/bin/python

import sqlite3
from sqlite3 import Error

def create_connection(dbfile):
	try:
		conn = sqlite3.connect(dbfile)
		return conn
	except Error as e:
		print(e)
	return None
	
def primary_research(conn):
	cur = conn.cursor()
	cur.execute('''SELECT COUNT(*) FROM nodes;''')
	rows = cur.fetchall()
	for row in rows:
		print "The number of nodes is " + str(row[0])
	
	cur.execute ('''SELECT COUNT(*) FROM ways;''')
	rows = cur.fetchall()
	for row in rows:
		print "The number of ways is " + str(row[0])
		
	cur.execute('''SELECT COUNT(DISTINCT(total.uid)) FROM
	(SELECT uid FROM nodes
	UNION ALL
	SELECT uid FROM ways) AS total;''')
	rows = cur.fetchall()
	for row in rows:
		print "The number of unique user is " + str(row[0])
		
	cur.execute('''SELECT  COUNT(value) FROM nodes_tags
	WHERE key = "amenity"
	AND value = "cafe";''')
	rows = cur.fetchall()
	for row in rows:
		print "The number of cafe is " + str(row[0])
	
	
def accessible_road(conn, selection):
	accessible_road =[]
	cur = conn.cursor()
	if selection == "yes":
		cur.execute('''SELECT  DISTINCT ways_tags.value FROM 
		(SELECT ways_tags.id FROM ways_tags
		WHERE  ways_tags.key = "wheelchair"
		AND ways_tags.value = "yes") as Result
		JOIN ways_tags
		ON ways_tags.id = Result.id
		WHERE ways_tags.key = "name";''')
	
	if selection == "limited":
		cur.execute('''SELECT  DISTINCT ways_tags.value FROM 
		(SELECT ways_tags.id FROM ways_tags
		WHERE  ways_tags.key = "wheelchair"
		AND ways_tags.value = "limited") as Result
		JOIN ways_tags
		ON ways_tags.id = Result.id
		WHERE ways_tags.key = "name";''')
	
	if selection == "all":
		cur.execute('''SELECT  DISTINCT ways_tags.value FROM 
		(SELECT ways_tags.id FROM ways_tags
		WHERE  ways_tags.key = "wheelchair"
		AND (ways_tags.value = "limited"
		OR ways_tags.value = "yes")) as Result
		JOIN ways_tags
		ON ways_tags.id = Result.id
		WHERE ways_tags.key = "name";''')

	rows = cur.fetchall()
	ind = 1
	for row in rows:
		accessible_road.append((ind, row[0].encode("utf-8")))
		ind +=1
	print accessible_road
		
def find_most_popular_cuisines(conn):
	cur = conn.cursor()
	cur.execute('''SELECT value, COUNT(*) as cuisine_count FROM nodes_tags
	WHERE key="cuisine"
	GROUP BY value
	ORDER BY cuisine_count DESC
	LIMIT 10;''')
	rows = cur.fetchall()
	for row in rows:
		cuisine = row[0].encode("utf-8")
		print cuisine + (20-len(cuisine))*" "+ "|" + str(row[1])

def find_all_fish_and_chips(conn):
	cur = conn.cursor()
	cur.execute('''SELECT COUNT(value) FROM nodes_tags
	WHERE key = "cuisine"
	AND value LIKE "%fish_and_chips%";''')
	rows = cur.fetchall()
	for row in rows:
		print row[0]

def audit_cardiff_postal_code(conn):
	cur = conn.cursor()
	cur.execute('''SELECT ways_tags.key, ways_tags.value FROM ways_tags JOIN
	(SELECT audit.value, audit.id
		FROM (SELECT * FROM nodes_tags 
			  UNION ALL 
			SELECT * FROM ways_tags) as audit
		WHERE (audit.key='postcode'
		OR audit.key = "postal_code")
		AND NOT audit.value LIKE "CF%"
		GROUP BY audit.value) as invalid
		ON invalid.id = ways_tags.id''')
	rows = cur.fetchall()
	print [(row[0].encode('utf-8'), row[1].encode('utf-8')) for row in rows]
	
def find_entries_have_both_postal_and_postcode(conn):
	cur = conn.cursor()
	cur.execute('''SELECT audit.value, audit.id, audit.key
	FROM (SELECT * FROM nodes_tags 
	UNION ALL 
	SELECT * FROM ways_tags) as audit
	jOIN (SELECT * FROM nodes_tags 
	UNION ALL 
	SELECT * FROM ways_tags) as audit_copy
	ON audit.id = audit_copy.id
	WHERE audit.id = audit_copy.id
	AND (audit.key = "postal_code" 
	AND audit_copy.key = "postcode")
	OR (audit_copy.key = "postal_code"
	AND audit.key = "postcode");''')
	rows = cur.fetchall()
	print [(row[0].encode('utf-8'), row[1], row[2].encode('utf-8')) for row in rows]
	
def main():
	database = "Open_Street_Data.db"
 	
	#Connect to the database

	conn = create_connection(database)
	with conn:
		
		print("1. Conducting Primary research")
		primary_research(conn)
 		print ("------------------------------\n")

		print("2. Find the most favourite cuisine, my guess is fish'n'chips...")
		find_most_popular_cuisines(conn)
		print ("After cleaning, the total fish_and_chips cuisine are ")
		find_all_fish_and_chips(conn)
		print ("------------------------------\n")
		
		print("3. Find all accessible places")
		print("Find all places with accessiblitiy support (labeled 'accssibility-yes')")
		accessible_road(conn, "yes")
		print ("Find all places with limited accessibility support (labeled 'accssibility-limited')")
		accessible_road(conn, "limited")
		print("Find all places with any kind of accessibility support\n(labeled 'accessibiltiy-limited\
 and labeled 'accessibility-all')")
		accessible_road(conn, "all")
		print ("------------------------------\n")
		
		
		print("4. Find invalid postal code")
		audit_cardiff_postal_code(conn)
		print("It seems that Roxy Court has both postal code and postcode keys\n and the postal code is written in the postal code field.\nI want to check if there are any other fields that have the same problem")
		find_entries_have_both_postal_and_postcode(conn)
		
		cur = conn.cursor()
		cur.execute('''
		SELECT value FROM ways_tags
		WHERE key = "phone";''')
		rows = cur.fetchall()
		phones = ([row[0].encode("utf-8").strip().replace(" ","").replace("", "").replace("+", ""). replace("-", "") \
		for row in rows])
		for phone in phones:
			phone = phone.decode("utf-8")
			for i in range(0, 1):
				if phone[i] not in str(range(1, 9)):
					phone = phone[1:]
			if phone[0] != "4" or phone[1] != "4":
				phone = "44" + phone 
			print phone
		
 
if __name__ == '__main__':
	main()