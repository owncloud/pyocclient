==================================
Python client library for ownCloud
==================================

This library makes it possible to connect to an ownCloud instance and perform
file, share and attribute operations in python.

Please note that this is **not** a sync client implementation but rather a wrapper
around various APIs.

See the `ownCloud homepage <http://owncloud.org>`_ for more information about ownCloud.

Features
========

Accessing files
---------------

- basic file operations like getting a directory listing, file upload/download, directory creation, etc
- read/write file contents from strings
- upload with chunking and mtime keeping
- upload whole directories
- directory download as zip

Sharing
-------

- share a file with public link using the OCS Share API

App data
--------

- store app data as key/values using the privatedata OCS API

Requirements
============

- Python >= 2.7 (no support for Python 3 yet)
- requests module (for making HTTP requests)

Installation
============

To install pyocclient, simply:

.. code-block:: bash

    $ pip install pyocclient

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

    $ cd doc
    $ make html

You can then find the documentation inside of "doc/build/html".

