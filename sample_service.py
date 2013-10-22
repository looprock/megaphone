#!/usr/bin/env python
import json
import sys
import os
from bottle import route, run, get
import time
import urllib
import urllib2

data = json.dumps({'id': 'bar', 'url': 'http://localhost:8081/q/status'})
url = "http://localhost:18001/check"
req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
f = urllib2.urlopen(req)
response = f.read()
f.close()

def usage():
        print "%s [status: OK,Unknown,Warning,Critical]" % (sys.argv[0])

t = len(sys.argv)
if t < 2:
        usage()
        sys.exit(1)
else:  
        statusm = sys.argv[1]

t = time.localtime()
ts = time.strftime('%Y-%m-%dT%H:%M:%S%Z', t)
rootdir = "/Users/dsl/code/python/metatron"

# Change working directory so relative paths (and template lookup) work again
root = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, root)

# generate nested python dictionaries, copied from here:
# http://stackoverflow.com/questions/635483/what-is-the-best-way-to-implement-nested-dictionaries-in-python
class AutoVivification(dict):
        """Implementation of perl's autovivification feature."""
        def __getitem__(self, item):
                try:
                        return dict.__getitem__(self, item)
                except KeyError:
                        value = self[item] = type(self)()
                        return value

def readfile(fname):
    try:
            f = open(fname, 'r')
            o = f.read()
            return re.sub(r'\0',' ',o)
            f.close()
    except:
        msg = "ERROR: reading %s failed!" % fname
        return msg

@route('/hello')
def hello():
	return "Hello World!"

@get('/q/status')
def status():
	data = AutoVivification()
	#data['status'] = readfile(rootdir + '/test/status.txt')
	#data['status'] = readfile('./test/status.txt')
	data['id'] = "bar"
	data['status'] = statusm
	data['date'] = ts
	data['message'] = "Everything is groovy man."
	data['version'] = "1.0.0"
	return data

run(host='localhost', port=8081, debug=True)
