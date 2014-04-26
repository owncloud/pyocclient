#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: expandtab shiftwidth=4 softtabstop=4
#
import time

# unique id to use for testing
test_id = int(time.time())

Config = {
    # Change this to your ownCloud's URL
    'owncloud_url': 'http://localhost/owncloud',
    # ownCloud login
    'owncloud_login': 'root',
    # ownCloud password
    'owncloud_password': 'admin',
    # remote root path to use for testing 
    'test_root': 'pyoctestroot%s' % test_id,
    # app name to use when testing privatedata API
    'app_name': 'pyocclient_test%s' % test_id
}

