#!/usr/bin/env python
"""Megaphone is an alerting consolidation service."""

import json
import sys
import os
import re
from bottle import Bottle
import time
import urllib2
import shutil
import bottle
from ConfigParser import SafeConfigParser
import logging
import multiprocessing
logging.basicConfig()

app = Bottle()

_basedir = os.path.abspath(os.path.dirname(__file__))
config = SafeConfigParser()
try:
    config.read('%s/megaphone.conf' % _basedir)
    DEBUG = config.getboolean('settings', 'DEBUG')
    QUIET = config.getboolean('settings', 'QUIET')
    CACHEDIR = config.get('settings', 'CACHEDIR')
    CACHEFILE = config.get('settings', 'CACHEFILE')
    WSGISERVER = config.get('settings', 'WSGISERVER')
    CACHE = "%s/%s" % (CACHEDIR, CACHEFILE)
    LISTEN = config.get('settings', 'LISTEN')
    PORT = config.get('settings', 'PORT')
    TIMEOUT = float(config.get('settings', 'TIMEOUT'))
except:
    print "INFO: unable to find config file, skipping"


if "MEGAPHONE_DEBUG" in os.environ:
    DEBUG = os.environ["MEGAPHONE_DEBUG"]

if "MEGAPHONE_QUIET" in os.environ:
    QUIET = os.environ["MEGAPHONE_QUIET"]

if "MEGAPHONE_WSGISERVER" in os.environ:
    WSGISERVER = os.environ["MEGAPHONE_WSGISERVER"]

if "MEGAPHONE_CACHE" in os.environ:
    CACHE = os.environ["MEGAPHONE_CACHE"]

if "MEGAPHONE_LISTEN" in os.environ:
    LISTEN = os.environ["MEGAPHONE_LISTEN"]

if "MEGAPHONE_PORT" in os.environ:
    PORT = os.environ["MEGAPHONE_PORT"]

if "MEGAPHONE_TIMEOUT" in os.environ:
    TIMEOUT = os.environ["MEGAPHONE_TIMEOUT"]

try:
    DEBUG
except:
    DEBUG = False

try:
    QUIET
except:
    QUIET = True

try:
    WSGISERVER
except:
    WSGISERVER = "default"

try:
    LISTEN
except:
    LISTEN = "0.0.0.0"

try:
    CACHE
except:
    CACHE = "/tmp/megaphone.json"

try:
    PORT
except:
    PORT = "18001"

try:
    TIMEOUT
except:
    TIMEOUT = 10


def bug(msg):
    """Print debug output."""
    if DEBUG:
        print "DEBUG: %s" % msg


class MyException(Exception):
    """Support unittesting."""

    pass


ts = time.strftime('%Y-%m-%dT%H:%M:%S%Z', time.localtime())

# Change working directory so relative paths (and template lookup) work again
root = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, root)

if os.path.isfile(CACHE):
    bug("CACHE: %s" % CACHE)
    with open(CACHE) as data_file:
        checks = json.load(data_file)
else:
    checks = {}

# we shouldn't write to tmp by default because our megaphone.json could get deleted by tmpwatch
if CACHE == "/tmp/megaphone.json":
    print "WARNING: cache set to %s, could get clobbered by tmpwatch!" % CACHE


def writecache(data):
	try:
		if os.path.isfile(CACHE):
			backup = "%s.backup" % CACHE
			shutil.copyfile(CACHE, backup)
		with open(CACHE, 'w') as outfile:
			json.dump(data, outfile)
	except:
		# it's bad news if we can't create a cache file to reload on restart,
		# throw an error in megaphone!
		print "ERROR: cache creation failed!"
		checks['--global'] = "ERROR: cache creation failed!"
		writecache(checks)

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

# read a file
def readfile(fname):
	try:
		f = open(fname, 'r')
		o = f.read()
		return re.sub(r'\0', ' ', o)
		f.close()
	except:
		msg = "Critical: reading %s failed!" % fname
		return msg

# read a megaphone compatible status url and return the object
def readstatus(name,url,q):
	bug("now in readstatus")
	result = {}
	validstatus = ["OK", "Unknown", "Warning", "Critical"]
	# this is to support status somewhere other than 'status' under the root of a service
	# {"id": "ok2_status", "url": {"addr": "http://localhost:18999/status", "jsonpath": "megaphone/status"}}
	if isinstance(url, dict):
		bug("url is a dictionary")
		data = AutoVivification()
		if 'addr' not in url:
			mymsg = "ERROR: couldn't find addr in url, nothing to check"
			bug(mymsg)
			data['status'] = "Critical"
			data['message'] = mymsg
		else:
			if 'jsonpath' in url:
				bug("parsing jsonpath and addr in url: jsonpath: %s, addr: %s" % (url['jsonpath'],url['addr']))
				try:
					tdata = json.load(urllib2.urlopen(url['addr'], timeout = TIMEOUT))
					v = "tdata"
					for i in url['jsonpath'].split("/"):
						bug("i: %s" % i)
						if i:  
							v += "['%s']" % i
					bug("eval type:")
					if DEBUG:
						print type(eval(v))
						print type(eval(v).encode('ascii','ignore'))
					data['status'] = eval(v)
					data['date'] = ts
					msg = "Status from path %s: %s" % (url['jsonpath'], data['status'])
					bug(msg)
					data['message'] = msg
				except:
					msg = "error collecting results from addr: %s, jsonpath: %s" % (url['addr'],url['jsonpath'])
					bug(msg)
					data['status'] = "Critical"
					data['date'] = ts
					data['message'] = msg
			else:
				bug("no jsonpath detected in url, using only addr path")
				try:
					data = json.load(urllib2.urlopen(url['addr'], timeout = TIMEOUT))
				except:
					msg = "timeout connecting to %s" % (url['addr'])
					bug(msg)
					data['status'] = "Critical"
					data['date'] = ts
					data['message'] = msg
			if 'statusoverride' in url:
				bug("statusoverride detected in url")
				if url['statusoverride'] not in validstatus:
					data['status'] = "Critical"
					data['message'] = "ERROR: invalid status '%s' written to statusoverride!" % url['statusoverride']
				else:
					data['status'] = url['statusoverride']
					data['message'] = "NOTICE: statusoverride used!"
	else:
		bug("url object isn't a dictionary, processing normally")
		try:
			data = json.load(urllib2.urlopen(url, timeout = TIMEOUT))
		except:
			data = AutoVivification()
			msg = "timeout connecting to %s" % (url)
			bug(msg)
			data['status'] = "Critical"
			data['date'] = ts
			data['message'] = msg
	if "status" not in data.keys():
		data['status'] = "Critical"
		data['message'] = "No status was found on given path!"
	if data["status"] not in validstatus:
		data['status'] = "Critical"
		data['message'] = "ERROR: status value '%s' not valid!" % data["status"]
	bug("Data:")
	if DEBUG:
		print data
	result[name] = data
	if DEBUG:
		print result
		print type(name)
		print type(result)
	if q:
		q.put(result)
	else:
		return data

def returnmsg(x,st):
	if 'message' not in x.keys():
		return "Detected %s state [no message specified]" % st
	else:
		return x['message']
	bug("message: %s" % mymsg)

def getallstatus():
	bug("Checks:")
	if DEBUG:
		print checks
	data = AutoVivification()
	# setting a global override. If there is a check with the id '--global',
	# only respect that. Always return Critical with a message of whatever is
	# in the url object
	if "--global" in checks.keys():
		bug("Found a global valuse in keys!")
		data['status'] = "Critical"
		data['message'] = checks['--global']
		data['date'] = ts
		return data
	# if there's no global override, parse the rest of the checks.
	else:
		# trying to conform to current monitoring status guidelines
		# http://nagiosplug.sourceforge.net/developer-guidelines.html#PLUGOUTPUT
		statusc = {
			"Warning":  0,
			"Critical":  0,
			"Unknown":  0,
			"OK": 0,
		}
		E = 0
		msg = ""
		# run all the checks in parallel
		q = multiprocessing.Queue()
		jobs = [multiprocessing.Process(target=readstatus, args=(i,checks[i],q,)) for i in checks.keys()]
		for job in jobs: job.start()
		for job in jobs: job.join()
		results = [q.get() for i in checks.keys()]
		bug("Results:")
		print results
		for y in results:
			i, x = y.popitem()
			# for all checks we're monitoring, capture the state and the message
			# figure out something to do with date testing
			# like throw an error if current date is > 5min from returned date
			bug("checking %s" % i)
			bug("check status response:")
			if DEBUG: 
				print x
			stattypes = ["Warning", "Critical", "OK"]
			if x['status'] in stattypes:
				bug("Detected %s status" % x['status'])
				mymsg = returnmsg(x,x['status'])
				bug("mymsg: %s" % mymsg)
				statusc[x['status']] = statusc[x['status']] + 1
				if x['status'] != "OK":
					msg += "%s:%s:%s|" % (i, x['status'], mymsg)
			else:
				mymsg = returnmsg(x,"Unknown")
				# things aren't Warning, Critical, or OK so something else is going on
				statusc['Unknown'] = statusc['Unknown'] + 1
				msg += "%s:%s:%s|" % (i, x['status'], mymsg)
		bug("All checks are checked!")

		# set the status to the most critical value in the order: Unknown, Warning, Critical
		# i.e. if WARNING is the worst issue, i present that, but if ERROR and
		# WARNING are both present use ERROR
		bug("finished all checks. Aggregating")
		if statusc['Unknown'] > 0:
			data['status'] = "Unknown"
			E = 1
			bug("Setting state to Unknown")
		if statusc['Warning'] > 0:
			data['status'] = "Warning"
			E = 1
			bug("Setting state to Warning")
		if statusc['Critical'] > 0:
			data['status'] = "Critical"
			E = 1
			bug("Setting state to Critical")

		# trim the value of msg since we're appending and adding ';' at the end for errors
		bug("E: %s" % str(E))
		if E > 0:
			data['message'] = msg[:-1]
			bug("final message - %s" % msg[:-1])
		else:
			if len(checks.keys()) > 0:
				bug("All checks are OK!")
				# we didn't find any error states, so we're OK
				data['status'] = "OK"
				data['message'] = "Everything is OK!"
			else:
				data['status'] = "Unknown"
				data['message'] = "No checks are registered!"
				bug("No checks are registered!")
		bug("adding timestamp")
		data['date'] = ts
		bug("results are in:")
		if DEBUG:
			print data
		return data

# list all megaphone checks
@app.get('/checks')
def list():
	data = AutoVivification()
	return checks

# add a check: {"id": "ok_status", "url": "http://localhost:18999/status"}
@app.post('/checks')
def add_submit():
	data = bottle.request.body.readline()
	if not data:
		app.abort(400, 'No data received')
	entity = json.loads(data)
	if 'id' not in entity:
		app.abort(400, 'No id specified')
	try:
		checks[entity["id"]] = entity["url"]
		writecache(checks)
	except:
		app.abort(400, "Error adding new check!")

# delete a check: {"id": "ok_status"}
@app.delete('/checks/:s')
def delcheck(s):
	try:
		del checks[s]
		writecache(checks)
	except:
		app.abort(400, "Error deleting check!")

# proxy the response of a status url megaphone is checking
@app.get('/checks/:s')
def checkshow(s):
	if s not in checks.keys():
		return "Sorry, no check %s registered!" % s
	else:
		if isinstance(checks[s], dict):
			if 'addr' not in checks[s]:
				return "Sorry, can't find a valid endpoint in your check!"
			else:
				try:
					res = json.load(urllib2.urlopen(checks[s]['addr'], timeout = TIMEOUT))
					if 'statusoverride' in checks[s]:
						res['status'] = checks[s]['statusoverride']
						res['message'] = "NOTICE: statusoverride used!"
					return res
				except:
					return "Error connecting to: %s" % checks[s]['addr']
		else:
			try:
				return json.load(urllib2.urlopen(checks[s], timeout = TIMEOUT))
			except:
				return "Error connecting to: %s" % checks[s]['addr']

# generate the main status output
@app.get('/')
def status():
	return getallstatus()

if __name__ == '__main__':
	try:
		if WSGISERVER != 'default':
			app.run(host=LISTEN, port=PORT, debug=DEBUG, quiet=QUIET, server=WSGISERVER)
		else:
			app.run(host=LISTEN, port=PORT, debug=DEBUG, quiet=QUIET)
	except KeyboardInterrupt:
		sys.exit("Aborted by Ctrl-C!")
