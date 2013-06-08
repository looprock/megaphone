Megaphone
=========

Megaphone is a bottle.py based service that is intended to proxy and collate JSON based status data in a centralized interface.

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

You can start megaphone by navigating to the directory it lives in and typing ./megaphone. It's packaged with bottle.py which is it's primary dependency. If you'd like to run it in a more production-ready manner you can use supervisor to manage it as a service.

Once megaphone is running, you register a check by posting JSON data consisting of {'id': 'some global id', 'url': 'http://some.status.url'}. Megaphone currently only pays attention to 'status' (in order of least to most critical: OK, Unknown, Warning, Critical) and 'message'. It will then process each check and present the most critical result returned from any one check as the result in the main /status page. It will present all messages returned higher than OK in the message result on the main /status page.

You can get a list of all the registered services by GETting /check/list. The entire JSON payload of a check can be retrieved by GETting /check/show/'id'

Below is an example session.

----------------------------------

# Megaphone Session

## Check initial status

GET: http://localhost:8080/status

RESULT: {"status": "Unknown", "date": "2013-06-06T14:49:26CDT", "message": "No services are registered!"}

## List current checks

GET: http://localhost:8080/check/list

RESULT: {}

## Add a check

initiate this by using: ./sample_service.py OK

PUT: http://localhost:8080/check/add

DATA: {"id": "bar", "url": "http://localhost:8081/q/status"}

## Verify check

GET: http://localhost:8080/check/list

RESULT: {"bar": "http://localhost:8081/q/status"}

## Check new status

GET: http://localhost:8080/status

RESULT: {"status": "OK", "date": "2013-06-06T14:49:26CDT", "message": "Everything is OK!"}

## Add another check

initiate this by using: ./sample_service2.py Warning

PUT: http://localhost:8080/check/add

DATA: {"id": "foo", "url": "http://localhost:8082/q/status"}

## Verify new check

GET: http://localhost:8080/check/list

RESULT: {"foo": "http://localhost:8082/q/status", "bar": "http://localhost:8081/q/status"

## Review new status

GET: http://localhost:8080/status

RESULT: {"status": "Warning", "date": "2013-06-06T14:49:26CDT", "message": "foo:Warning:Houston, I think we have a problem."}

## View full status from check 'foo'

GET: http://localhost:8080/check/show/foo:

RESULT: {"status": "Warning", "date": "2013-06-06T14:54:21CDT", "message": "Houston, I think we have a problem.", "version": "2.0.0", "id": "foo"}

## View full status from check 'bar'

GET: http://localhost:8080/check/show/bar:

RESULT: {"status": "OK", "date": "2013-06-06T14:51:56CDT", "message": "Everything is groovy man.", "version": "1.0.0", "id": "bar"}
