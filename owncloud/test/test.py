#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: expandtab shiftwidth=4 softtabstop=4
#
import unittest
import os
import shutil
import owncloud
import datetime
import time
import tempfile
import requests

from config import Config

class TestFileAccess(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.gettempdir() + '/pyocclient_test%s/' % int(time.time())
        os.mkdir(self.temp_dir)
        self.client = owncloud.Client(Config['owncloud_url'])
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])
        self.test_root = Config['test_root']
        if not self.test_root[-1] == '/':
            self.test_root += '/'
        if not self.test_root[0] == '/':
            self.test_root = '/' + self.test_root
        self.client.mkdir(self.test_root)

    def tearDown(self):
        self.client.delete(self.test_root)
        self.client.logout()
        shutil.rmtree(self.temp_dir)

    @staticmethod
    def __create_file(target_file, size):
        file_handle = open(target_file, 'w')
        dummy_data = ''
        for i in range(0, 1024):
            dummy_data += 'X'

        for i in range(0, size / 1024):
            # write in 1kb blocks
            file_handle.write(dummy_data)
        file_handle.close()

    def test_mkdir(self):
        """Test subdirectory creation"""
        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))

    def test_put_file_contents(self):
        """Test creating remote file with given contents"""
        self.assertTrue(self.client.put_file_contents(self.test_root + 'test.txt', 'hello world!'))

    def test_get_file_contents(self):
        """Test reading remote file"""
        self.assertTrue(self.client.put_file_contents(self.test_root + 'test.txt', 'hello world!'))
        self.assertEquals(self.client.get_file_contents(self.test_root + 'test.txt'), 'hello world!')

    def test_get_file_info(self):
        """Test getting file info"""
        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'test.txt', 'hello world!'))

        file_info = self.client.file_info(self.test_root + 'test.txt')
        dir_info = self.client.file_info(self.test_root + 'subdir')

        self.assertTrue(isinstance(file_info, owncloud.FileInfo))
        self.assertTrue(isinstance(dir_info, owncloud.FileInfo))

        self.assertEquals(file_info.get_name(), 'test.txt')
        self.assertEquals(file_info.get_size(), 12)
        self.assertIsNotNone(file_info.get_etag())
        self.assertEquals(file_info.get_content_type(), 'text/plain')
        self.assertTrue(type(file_info.get_last_modified()) is datetime.datetime)
        self.assertFalse(file_info.is_dir())

        self.assertEquals(dir_info.get_name(), 'subdir')
        self.assertIsNone(dir_info.get_size())
        self.assertIsNotNone(dir_info.get_etag())
        self.assertEquals(dir_info.get_content_type(), 'httpd/unix-directory')
        self.assertTrue(type(dir_info.get_last_modified()) is datetime.datetime)
        self.assertTrue(dir_info.is_dir())

    def test_get_file_info_non_existing(self):
        """Test getting file info for non existing file"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + 'unexist')
        self.assertEquals(e.exception.status_code, 404)

    def test_get_file_listing(self):
        """Test getting file listing"""
        self.assertTrue(self.client.put_file_contents(self.test_root + 'file one.txt', 'first file'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'zzz.txt', 'z file'))
        self.assertTrue(self.client.put_file_contents(self.test_root + u'中文.txt', ''))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'abc.txt', ''))
        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'subdir/in dir.txt', ''))

        listing = self.client.list(self.test_root)
        self.assertEquals(len(listing), 5)
        self.assertEquals(listing[0].get_name(), 'abc.txt')
        self.assertEquals(listing[1].get_name(), 'file one.txt')
        self.assertEquals(listing[2].get_name(), 'subdir')
        self.assertEquals(listing[3].get_name(), 'zzz.txt')
        self.assertEquals(listing[4].get_name(), '中文.txt')

        self.assertTrue(listing[2].is_dir())
        self.assertFalse(listing[3].is_dir())

    def test_get_file_listing_non_existing(self):
        """Test getting file listing for non existing directory"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.list(self.test_root + 'unexist')
        self.assertEquals(e.exception.status_code, 404)

    def test_upload_small_file(self):
        """Test simple upload"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 2 * 1024)
        self.assertTrue(self.client.put_file(self.test_root + 'upload_test.dat', temp_file))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.test_root + 'upload_test.dat')

        self.assertIsNotNone(file_info)
        self.assertEquals(file_info.get_size(), 2 * 1024)

    def test_upload_big_file(self):
        """Test chunked upload"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 22 * 1024 * 1024)
        self.assertTrue(self.client.put_file(self.test_root + 'chunk_test.dat', temp_file))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.test_root + 'chunk_test.dat')

        self.assertIsNotNone(file_info)
        self.assertEquals(file_info.get_size(), 22 * 1024 * 1024)

    def test_upload_timestamp(self):
        # TODO: test with keeping timestamp and not keeping it
        pass

    def test_upload_directory(self):
        temp_dir = self.temp_dir + 'pyoctest.dir/'
        os.mkdir(temp_dir)
        os.mkdir(temp_dir + 'levelone')
        os.mkdir(temp_dir + 'levelone/leveltwo')

        self.__create_file(temp_dir + 'file1.dat', 2 * 1024)
        self.__create_file(temp_dir + 'file2.dat', 22 * 1024 * 1024)
        self.__create_file(temp_dir + 'levelone/file3.dat', 22 * 1024 * 1024)
        self.__create_file(temp_dir + 'levelone/leveltwo/file4.dat', 8 * 1024 * 1024)

        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_directory(self.test_root + 'subdir', temp_dir))

        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/file1.dat'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/file2.dat'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/levelone/file3.dat'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/levelone/leveltwo/file4.dat'))

    def test_download_file(self):
        """Test file download"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.assertTrue(self.client.put_file_contents(self.test_root + 'test.txt', 'hello world!'))
       
        self.assertTrue(self.client.get_file(self.test_root + 'test.txt', temp_file))

        f = open(temp_file, 'r')
        s = f.read()
        f.close()

        os.unlink(temp_file)

        self.assertEquals(s, 'hello world!')

    def test_download_dir(self):
        import zipfile
        """Test directory download as zip"""
        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'subdir/test.txt', 'hello world!'))

        temp_file = self.temp_dir + 'pyoctest.zip'
        self.assertTrue(self.client.get_directory_as_zip(self.test_root, temp_file))

        self.assertTrue(os.stat(temp_file))

        zip_info = zipfile.ZipFile(temp_file)
        listing = zip_info.namelist()
        
        self.assertEquals(len(listing), 3)
        os.unlink(temp_file)

    def test_delete_file(self):
        """Test file deletion"""
        self.assertTrue(self.client.put_file_contents(self.test_root + 'test.txt', 'hello world!'))
        self.assertTrue(self.client.delete(self.test_root + 'test.txt'))
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + 'test.txt')
        self.assertEquals(e.exception.status_code, 404)

    def test_delete_dir(self):
        """Test directory deletion"""
        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'subdir/test.txt', 'hello world!'))
        self.assertTrue(self.client.delete(self.test_root + 'subdir'))
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + 'subdir/test.txt')
        self.assertEquals(e.exception.status_code, 404)
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + 'subdir')
        self.assertEquals(e.exception.status_code, 404)

    def test_share_with_link(self):
        """Test sharing a file with link"""
        self.assertTrue(self.client.put_file_contents(self.test_root + 'test.txt', 'hello world!'))

        share_info = self.client.share_file_with_link(self.test_root + 'test.txt')

        self.assertTrue(isinstance(share_info, owncloud.PublicShare))
        self.assertTrue(type(share_info.share_id) is int)
        self.assertEquals(share_info.target_file, self.test_root + 'test.txt')
        self.assertTrue(type(share_info.link) is str)
        self.assertTrue(type(share_info.token) is str)

    def test_share_with_link_non_existing_file(self):
        """Test sharing a file with link"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.share_file_with_link(self.test_root + 'unexist.txt')
        self.assertEquals(e.exception.status_code, 404)

class TestPrivateDataAccess(unittest.TestCase):
    def setUp(self):
        self.client = owncloud.Client(Config['owncloud_url'])
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])
        self.app_name = Config['app_name']

    def tearDown(self):
        # TODO: delete all attributes ?
        self.assertTrue(self.client.delete_attribute(self.app_name, 'attr1'))
        self.client.logout()

    def test_set_attribute(self):
        """Test setting an attribute"""
        self.assertTrue(self.client.set_attribute(self.app_name, 'attr1', 'value1'))

    def test_get_attribute(self):
        """Test getting an attribute"""
        self.assertTrue(self.client.set_attribute(self.app_name, 'attr1', 'value1'))

        self.assertEquals(self.client.get_attribute(self.app_name, 'attr1'), 'value1')
        self.assertEquals(self.client.get_attribute(self.app_name), [('attr1', 'value1')])

    def test_get_non_existing_attribute(self):
        """Test getting the value of a non existing attribute"""
        self.assertIsNone(self.client.get_attribute(self.app_name, 'unexist'))

    def test_set_attribute_empty(self):
        """Test setting an attribute to an empty value"""
        self.assertTrue(self.client.set_attribute(self.app_name, 'attr1', ''))
        self.assertEquals(self.client.get_attribute(self.app_name, 'attr1'), '')
        self.assertEquals(self.client.get_attribute(self.app_name), [('attr1', '')])

    def test_delete_attribute(self):
        """Test deleting an attribute"""
        self.assertTrue(self.client.set_attribute(self.app_name, 'attr1', 'value1'))
        self.assertEquals(self.client.get_attribute(self.app_name, 'attr1'), 'value1')

        self.assertTrue(self.client.delete_attribute(self.app_name, 'attr1'))

        self.assertIsNone(self.client.get_attribute(self.app_name, 'attr1'))
        self.assertEquals(self.client.get_attribute(self.app_name), [])

if __name__ == '__main__':
    unittest.main()

