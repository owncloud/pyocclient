#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: expandtab shiftwidth=4 softtabstop=4
#
import os
import owncloudclient

# Change this to your ownCloud's URL
owncloud_url = 'http://localhost/owncloud'
# ownCloud login
owncloud_login = 'root'
# ownCloud password
owncloud_password = 'admin'
# remote root path to use for this demo
test_root = 'pyoctestroot'
# app name to use when testing privatedata API
app_name = 'pyocclient_demo'

def create_file(target_file, size):
    file_handle = open(target_file, 'w')
    dummy_data = ''
    for i in range(0, 1024):
        dummy_data += 'X'

    for i in range(0, size / 1024):
        # write in 1kb blocks
        file_handle.write(dummy_data)
    file_handle.close()


def run_demo():
    oc = owncloudclient.Client(owncloud_url)

    if not oc.login(owncloud_login, owncloud_password):
        return False

    # Create the test directory
    print "Create the test directory"
    print oc.mkdir(test_root)
    print oc.mkdir(test_root + 'subdir')
    print

    # Create a remote file with given contents
    print "Create remote files with given contents"
    print oc.put_file_contents(test_root + 'test.txt', 'hello world!')
    print oc.put_file_contents(test_root + 'test2.txt', 'hello world again!')
    print

    # Read out the content
    print "Read out the content: \"",
    contents = oc.get_file_contents(test_root + 'test.txt')
    print contents, "\""
    print

    # Get file info
    print "Get file info"
    print oc.file_info(test_root + 'test.txt')
    print

    # Get file listing
    print "Get file listing"
    print oc.list(test_root)
    print

    temp_file = '/tmp/pyoctest.dat'

    # Create a big local file with random data (22 MB)
    create_file(temp_file, 22 * 1024 * 1024)

    # Upload file (this will trigger chunking)
    print "Upload a big file"
    print oc.put_file(test_root + 'chunk_test.dat', temp_file)
    print

    os.unlink(temp_file)

    # Download that file
    print "Download that file"
    print oc.get_file(test_root + 'chunk_test.dat', temp_file)
    print

    os.unlink(temp_file)

    # Delete the remote file
    print "Delete that file"
    print oc.delete(test_root + 'chunk_test.dat')
    print

    # Share test file with link
    print "Share test file with link: ",
    share_info = oc.share_file_with_link(test_root + 'test.txt')
    print share_info.link
    print

    # Download directory as zip
    print oc.get_directory_as_zip(test_root, '/tmp/pyoctest.zip')
    os.unlink('/tmp/pyoctest.zip')

    # Delete test directory
    print "Delete test root"
    print oc.delete(test_root)
    print

    print "Set app attributes"
    print oc.set_attribute(app_name, 'attr1', 'value1')
    print oc.set_attribute(app_name, 'attr2', 'value2')
    print

    print "Get app attribute value: \"",
    print oc.get_attribute(app_name, 'attr1'), "\""
    print

    print "Get all app attributes: ",
    print oc.get_attribute(app_name)
    print

    print "Delete attributes"
    print oc.delete_attribute(app_name, 'attr1')
    print oc.delete_attribute(app_name, 'attr2')
    print

    print "Log out"
    print oc.logout()
    print

    return True

if __name__ == '__main__':
    if not test_root[-1] == '/':
        test_root += '/'

    if not run_demo():
        print "Could not login, please check the URL and credentials inside this script"

