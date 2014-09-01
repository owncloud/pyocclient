==================================
Python client library for ownCloud
==================================

.. image:: https://travis-ci.org/PVince81/pyocclient.svg?branch=master
    :target: https://travis-ci.org/PVince81/pyocclient

This library makes it possible to connect to an ownCloud instance and perform
file, share and attribute operations in python.

Please note that this is **not** a sync client implementation but rather a wrapper
around various APIs.

See the `ownCloud homepage <http://owncloud.org>`_ for more information about ownCloud.

Features
========

Supports connecting to ownCloud 5, 6 and 7.

Please note that ownCloud 5 will require setting the "single_session"
constructor option to False for some API calls.

General information
-------------------

- retrieve information about ownCloud instance (e.g. version, host, URL, etc.)

Accessing files
---------------

- basic file operations like getting a directory listing, file upload/download, directory creation, etc
- read/write file contents from strings
- upload with chunking and mtime keeping
- upload whole directories
- directory download as zip

Sharing (OCS Share API)
-----------------------

- share a file/directory via public link
- share a resource with another user
- unshare a file or directory
- check if a file/directory is already shared
- get information about a shared resource

App data
--------

- store app data as key/values using the privatedata OCS API

Requirements
============

- Python >= 2.7 (no support for Python 3 yet)
- requests module (for making HTTP requests)

Installation
============

Automatic installation with pip:

.. code-block:: bash

    $ pip install pyocclient

Manual installation of development version with git:

.. code-block:: bash

    $ pip install requests
    $ git clone https://github.com/PVince81/pyocclient.git
    $ cd pyocclient
    $ python setup.py install

Usage
=====

Example for uploading a file then sharing with link:

.. code-block:: python

    import owncloud

    oc = owncloud.Client('http://domain.tld/owncloud')

    oc.login('user', 'password')

    oc.mkdir('testdir')

    oc.put_file('testdir/remotefile.txt', 'localfile.txt')

    link_info = oc.share_file_with_link('testdir/remotefile.txt')

    print "Here is your link: http://domain.tld/owncloud/" + link_info.link

Running the unit tests
======================

To run the unit tests, edit the config file in "owncloud/test/config.py" to
point to a running ownCloud instance to test against.
Then run the script "runtests.py":

.. code-block:: bash

    $ ./runtests.py

Building the documentation
==========================

To build the documentation, you will need to install Sphinx and docutil.
Then run the following commands:

.. code-block:: bash

    $ cd docs
    $ make html

You can then find the documentation inside of "doc/build/html".

Authors
=======

- Vincent Petry (@pvince81)
- Steffen Lindner (@gomezr)
- Soal (@soalhn)
