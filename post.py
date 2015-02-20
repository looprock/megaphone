#!/usr/bin/env python
import json
import sys
import requests
import os
import getopt
import socket

def usage():
	print sys.argv[0] + """ [options] [json file]
	options:

	-h/--help         -  print usage summary
	-o/--override     -  override the status
"""

statusoverride = False

try:                                
	opts, remainder = getopt.gnu_getopt(sys.argv[1:], "ho:", ["help", "override="])
except getopt.GetoptError:          
	usage()                         
	sys.exit(2) 

for opt, arg in opts:                
	if opt in ("-h", "--help"):      
		usage()                     
		sys.exit()                  
	elif opt in ("-o", "--override"):
		statusoverride = arg

if len(remainder) < 1:
	usage()
	sys.exit()

if statusoverride:
	validstatus = ["OK", "Unknown", "Warning", "Critical"]
	if statusoverride not in validstatus:
		print "ERROR: invalid override. Valid values are:"
		for i in validstatus:
			print i
		sys.exit(1)


datafile = remainder[0]

if os.path.isfile(datafile) == True:
	with open(datafile) as data_file:
		input = json.load(data_file)

# {"id": "adi", "url": {"addr": "http://fenode3.oak.vast.com:18003/status/adi", "statusoverride": "Critical"}}
if isinstance(input['url'], dict):
	input['url']['statusoverride'] = statusoverride
	t = input['url']['addr'].split(":")
	input['url']['addr'] = "http://%s:%s" % (socket.gethostname(), t[2])
else:
	t = input['url'].split(":")
	addr = "http://%s:%s" % (socket.gethostname(), t[2])
	input.pop("url", None)
	input['url'] = {}
	input['url']['addr'] = addr

if statusoverride:
	input['url']['statusoverride'] = statusoverride

r = requests.post("http://localhost:18001/checks", data=json.dumps(input))
if r.status_code == 200:
	print "SUCCESS! megaphone updated!"
else:
	print "ERROR: request failed with status code %s" % str(r.status_code)
	sys.exit(1)
