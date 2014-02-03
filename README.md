Megaphone
=========

Megaphone is a bottle.py based service that is intended to proxy and collate JSON based status data in a centralized service.

The idea is to provide a per system consistent API for checking the status of all services on that system. This means:

A) Any service that is registered or discovered on a box will instantly be monitored

B) Operations will always know how to monitor a new system

## Who talks to megaphone?

The intended targets of this data are things like monitoring systems and load-balancers. 

## Why JSON?

By using object based data, application developers can add or remove fields they care about without effecting the operations of megaphone.

## Why a local service?

By running this locally you get access to process lists and local commands for things like auto-discovery. This also allows you access to local services data and commands without running through additional proxies or worrying about remote execution.

## What about centralizing the data?

Megaphone can be used push data to any central store you'd like to use. The initial target will be zookeeper, but it could just as easily be pushed or pulled into a nosql, RDBMS, or other solution.

## How do I use Megaphone?
Install the requirements with pip lile
 pip install -r requirements.txt

Configure megaphone.conf

Start the service with:
 python megaphone.py 

If you'd like to run it in a more production-ready manner you can use supervisor to manage it as a service.

Once megaphone is running, you register a check by posting JSON data consisting of {'id': 'some global id', 'url': 'http://some.status.url'}. Megaphone currently only pays attention to 'status' (in order of least to most critical: OK, Unknown, Warning, Critical) and 'message'. It will then process each check and present the most critical result returned from any one check as the result in the main status page. It will present all messages returned higher than OK in the message result on the main status page.

You can get a list of all the registered services by GETting /checks. The entire JSON payload of a check can be retrieved by GETting /checks/'id'

Below is an example session.

----------------------------------

# Megaphone Session

## Check initial status

METHOD GET: http://localhost:18001/

RESULT: {"status": "Unknown", "date": "2013-06-06T14:49:26CDT", "message": "No services are registered!"}

## List current checks

METHOD GET: http://localhost:18001/checks

RESULT: {}

## Add a check

initiate this by using: ./sample_service.py OK

METHOD POST: http://localhost:18001/checks

DATA: {"id": "bar", "url": "http://localhost:18081/status"}

If 'status' isn't in the root of your JSON output, you can pass two objects, 'addr' and 'jsonpath', inside 'url':<br>
addr - the full URL for your check, exactly what you'd pass inside url if status was in the root of your JSON output<br>
jsonpath - a slash delimited 'path' to you status. 

for instance if your check output looks like this:<br>
{"megaphone": {"status": "OK", "date": "2014-02-01T23:36:38CST", "message": "Everything is OK!", "id": "ok"}}

You would use this to register your check:<br>
DATA: {"id": "bar", "url": {"addr": "http://localhost:18081/status", "jsonpath": "megaphone/status"}}

## Verify check

METHOD GET: http://localhost:18001/checks

RESULT: {"bar": "http://localhost:18081/status"}

## Check new status

METHOD GET: http://localhost:18001/

RESULT: {"status": "OK", "date": "2013-06-06T14:49:26CDT", "message": "Everything is OK!"}

## Add another check

initiate this by using: ./sample_service2.py Warning

METHOD POST: http://localhost:18001/checks

DATA: {"id": "foo", "url": "http://localhost:18082/status"}

## Verify new check

METHOD GET: http://localhost:18001/checks

RESULT: {"foo": "http://localhost:18082/status", "bar": "http://localhost:18081/status"

## Review new status

METHOD GET: http://localhost:18001/

RESULT: {"status": "Warning", "date": "2013-06-06T14:49:26CDT", "message": "foo:Warning:Houston, I think we have a problem."}

## View full status from check 'foo'

METHOD GET: http://localhost:18001/checks/foo:

RESULT: {"status": "Warning", "date": "2013-06-06T14:54:21CDT", "message": "Houston, I think we have a problem.", "version": "2.0.0", "id": "foo"}

## View full status from check 'bar'

METHOD GET: http://localhost:18001/checks/bar:

RESULT: {"status": "OK", "date": "2013-06-06T14:51:56CDT", "message": "Everything is groovy man.", "version": "1.0.0", "id": "bar"}

## Delete check 'bar'

METHOD DELETE: http://localhost:18001/checks/bar

# Tests:

Now there are tests for the development of megaphone. Run them with nosetest.

# Errata

megaphone can also update zookeeper (currently add only) with applications that register with it. You just need to create a config file (./zk.conf or /etc/zktools/zk.conf) with the right entries. 
