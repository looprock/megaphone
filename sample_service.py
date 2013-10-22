#!/usr/bin/env python
import json
import sys
import os
from bottle import route, run, get
import time
import httplib

server = "127.0.0.1"
statport = "18081"
host = "%s:18001" % server
staturl = "http://%s:%s/status" % (server,statport)

blob = {"id": "bar", "url": staturl}
data = json.dumps(blob)
connection =  httplib.HTTPConnection(host)
connection.request('POST', '/checks', data)
result = connection.getresponse()
print "RESULT: %s - %s" % (result.status, result.reason)

def usage():
        print "%s [status: OK,Unknown,Warning,Critical]" % (sys.argv[0])

msgs = {
	"OK": "Everything is groovy!",
	"Unknown": "Unknown error!",
	"Warning": "Houston, I think we have a problem.",
	"Critical": "Danger Will Rogers! Danger!"
}

t = len(sys.argv)
if t < 2:
        usage()
        sys.exit(1)
else:  
        statusm = sys.argv[1]



t = time.localtime()
ts = time.strftime('%Y-%m-%dT%H:%M:%S%Z', t)
rootdir = "./"

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

@get('/status')
def status():
	data = AutoVivification()
	data['id'] = "bar"
	data['status'] = statusm
	data['date'] = ts
	data['message'] = msgs[statusm]
	data['version'] = "1.0.0"
	return data

run(host='localhost', port=statport, debug=True)
