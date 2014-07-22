# -*- coding: utf-8 -*-
# vim: expandtab shiftwidth=4 softtabstop=4
#
import time

# unique id to use for testing
test_id = int(time.time())

Config = {
    # Change this to your ownCloud's URL
    'owncloud_url': 'https://cloud.portknox.net',
    # ownCloud login
    'owncloud_login': 'gomez',
    # ownCloud password
    'owncloud_password': '1Schibardo9@',
    # remote root path to use for testing 
    'test_root': 'pyoctestroot%s' % test_id,
    # app name to use when testing privatedata API
    'app_name': 'pyocclient_test%s' % test_id,
    # single session mode (only set to False for ownCloud 5)
    'single_session': True
}

