#!/usr/bin/env python
import json
import sys
import os
from bottle import Bottle
import time
import urllib2
import shutil
import socket
from ConfigParser import SafeConfigParser


app = Bottle()


debug = "false"


def bug(msg):
    if debug == 'true':
        print "DEBUG: %s" % msg

# zookeeper reporting
# if we find ./zk.conf or /etc/zktools/zk.conf, we should try to report to
# zookeeper
enablezk = "false"
if os.path.exists('./zk.conf'):
    enablezk = "true"
    bug("using config ./zk.conf")
    parser = SafeConfigParser()
    parser.read('./zk.conf')
elif os.path.exists('/etc/zktools/zk.conf'):
    enablezk = "true"
    bug("Using config /etc/zktools/zk.conf")
    parser = SafeConfigParser()
    parser.read('/etc/zktools/zk.conf')

if enablezk == "true":
    from kazoo.client import KazooClient
    from kazoo.retry import KazooRetry
    from kazoo.exceptions import KazooException
    env = parser.get('default', 'env').strip()
    zkserver = parser.get(env, 'server').strip()
    zkport = parser.get(env, 'port').strip()
    zkroot = parser.get(env, 'root').strip()
    server = "%s:%s" % (zkserver, zkport)
    host = socket.gethostname()
    kr = KazooRetry(max_tries=3)
    zk = KazooClient(hosts=server)

    def loadzk(data):
        if debug == "true":
            print data
        zk.start()
        for i in data.keys():
            if debug == "true":
                print data[i]
            path = '%s/envs/%s/applications/%s/content/servers/%s/megaphone/url' % (
                zkroot, env, i, host)
            if kr(zk.exists, path) == None:
                try:
                    kr(zk.create, path, value=str(data[i]), makepath=True)
                except KazooException:
                    cancelled = False
                    raise
        zk.stop()
else:
    # if zookeeper is disabled, just output if debug == true
    def loadzk(data):
        bug("zookeeper support not enabled, not submitting zNode data for record:")
        if debug == "true":
            print data

# end zookeeper reporting

t = time.localtime()
ts = time.strftime('%Y-%m-%dT%H:%M:%S%Z', t)

# Change working directory so relative paths (and template lookup) work again
root = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, root)

if os.path.isdir("/opt/megaphone/cache"):
    cache = "/opt/megaphone/cache/cache.json"
else:
    cache = "/tmp/cache.json"

if os.path.isfile(cache) == True:
    bug("cache: %s" % cache)
    with open(cache) as data_file:
        checks = json.load(data_file)
        loadzk(checks)
else:
    checks = {}

# we shouldn't write to tmp by default because our cache.json could get
# deleted by tmpwatch, etc.
if cache == "/tmp/cache.json":
    # i was originally going to use the --global override to inject a message, but decided against it
    # checks['--global'] = "ERROR: cache set to %s, will likely get clobbered by tmpwatch!" % cache
    print "WARNING: cache set to %s, could get clobbered by tmpwatch!" % cache


def writecache(data):
    try:
        if os.path.isfile(cache) == True:
            backup = "%s.backup" % cache
            shutil.copyfile(cache, backup)
        with open(cache, 'w') as outfile:
            json.dump(data, outfile)
            loadzk(data)
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

# read a megaphone compatable status url and return the object


def readstatus(url):
    try:
        data = json.load(urllib2.urlopen(url))
        return data
    except:
        pdata = AutoVivification()
        #pdata = {}
        pdata['status'] = "Critical"
        pdata['date'] = ts
        msg = "Unable to communicate with %s!" % url
        pdata['message'] = msg
        return pdata

# list all megaphone checks


@app.get('/check/list')
def list():
    data = AutoVivification()
    return checks

# add a check: {"id": "ok_status", "url": "http://localhost:18999/status"}


@app.post('/check/add')
def add_submit():
    data = app.request.body.readline()
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


@app.post('/check/del')
def delcheck():
    data = app.request.body.readline()
    if not data:
        app.abort(400, 'No data received')
    entity = json.loads(data)
    if 'id' not in entity:
        app.abort(409, 'No id specified')
    try:
        del checks[entity["id"]]
        writecache(checks)
    except:
        app.abort(400, "Error deleting check!")

# proxy the response of a status url megaphone is checking


@app.get('/check/show/:s')
def checkshow(s):
    #data = AutoVivification()
    #data = readstatus(checks[s])
    return readstatus(checks[s])
    # return data

# generate the main status output


@app.get('/status')
def status():
    data = AutoVivification()
    # setting a global override. If there is a check with the id '--global',
    # only respect that. Always return Critical with a message of whatever is
    # in the url object
    if "--global" in checks.keys():
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
        }
        E = 0
        msg = ""
        for i in checks.keys():
        # for all checks we're monitoring, capture the state and the message
        # figure out something to do with date testing
        # like throw an error if current date is > 5min from returned date
            x = readstatus(checks[i])
            if x['status'] == "Warning":
                if 'message' not in x.keys():
                    mymsg = 'Detected Warning state [no message specified]'
                else:
                    mymsg = x['message']
                statusc['Warning'] = statusc['Warning'] + 1
                msg += "%s:%s:%s|" % (i, x['status'], mymsg)
            elif x['status'] == "Critical":
                if 'message' not in x.keys():
                    mymsg = 'Detected Critical state [no message specified]'
                else:
                    mymsg = x['message']
                statusc['Critical'] = statusc['Critical'] + 1
                msg += "%s:%s:%s|" % (i, x['status'], mymsg)
            elif x['status'] == "OK":
                # Throw it away
                throwaway = "ok"
            else:
                if 'message' not in x.keys():
                    mymsg = 'Detected Unknown state [no message specified]'
                else:
                    mymsg = x['message']
                # things aren't Warning, Critical, or OK so something else is
                # going on
                statusc['Unknown'] = statusc['Unknown'] + 1
                msg += "%s:%s:%s|" % (i, x['status'], mymsg)

        # set the status to the most critical value in the order: Unknown, Warning, Critical
        # i.e. if WARNING is the worst issue, i present that, but if ERROR and
        # WARNING are both present use ERROR
        if statusc['Unknown'] > 0:
            data['status'] = "Unknown"
            E = 1
        if statusc['Warning'] > 0:
            data['status'] = "Warning"
            E = 1
        if statusc['Critical'] > 0:
            data['status'] = "Critical"
            E = 1

        # trim the value of msg since we're appending and adding ';' at the end
        # for errors
        if E > 0:
            data['message'] = msg[:-1]
        else:
            if len(checks.keys()) > 0:
                # we didn't find any error states, so we're OK
                data['status'] = "OK"
                data['message'] = "Everything is OK!"
            else:
                data['status'] = "Unknown"
                data['message'] = "No checks are registered!"
        data['date'] = ts
        return data

if __name__ == '__main__':
    # TODO make debug configurable
    app.run(host='0.0.0.0', port=18001, debug=True)
