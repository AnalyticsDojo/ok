ok.py
=====

The ok.py client script supports programming projects by running tests, tracking
progress, and assisting in debugging. The ok.py server performs and displays
analysis of student progress based on logging sent from the client script.

(Coming soon) Visit http://okpy.org to use our hosted service for your course.

The ok.py software was developed for CS 61A at UC Berkeley.

Installation
-------------
* Clone this repo
* Install [Google App Engine SDK](https://developers.google.com/appengine/downloads) and add it to your `$PATH`. You can do `brew install google-app-engine` on a mac.
* `export GAE_SDK=<location of unzipped GAE SDK>`
  - For brew, this location should be in /usr/local/Cellar/google-app-engine/1.9.8/share/google-app-engine.
  - Some files that should be present when running `ls $GAE_SDK` are `dev_appserver.py` and `api_server.py`.
* Install `virtualenv`. You can do `brew install virtualenv` on a mac or `pip install virtualenv` or `apt-get install python-virtualenv`
* Run `install.py`

Testing the Installation
------------------------
* Run `./run_tests`. For a successful installation, all tests should pass.

Starting the Server
-------------
```bash
$ cd server
$ ./start_server
```

Server Development
------------------

The server is developed in Python 2.7+ using the Google App Engine framework.

To start making changes to the server, first change to its virtual enviroment.

``source activate-server.sh``

In most environments, your prompt will change to start with ``(server)``.
To exit this environment, type ``deactivate``.

Core Features
-------------

TODO

Projects using ok.py
--------------------

TODO

Developer Guidelines
--------------------

TODO
