# -*- coding: utf-8 -*-
# vim: expandtab shiftwidth=4 softtabstop=4
#
import unittest
from unittest_data_provider import data_provider
import os
import shutil
import owncloud
import datetime
import time
import tempfile
import random
import six

from config import Config

def getSupportedDavVersion():
    # connect just to check supported DAV version
    client = owncloud.Client(Config['owncloud_url'])
    client.login(Config['owncloud_login'], Config['owncloud_password'])

    caps = client.get_capabilities()
    dav_version = None

    if 'dav' in caps and 'chunking' in caps['dav']:
        dav_version = float(caps['dav']['chunking'])

    return dav_version

def skipIfDavVersionLessThan(expected_version):
    dav_version = getSupportedDavVersion()
    if dav_version is None or dav_version < expected_version:
        return unittest.skip("Expected DAV version %s not supported in this ownCloud version" % expected_version)
    return lambda func: func

class TestFileAccess(unittest.TestCase):

    def get_dav_endpoint_version(self):
        return 0

    def files():
        return (
            ['test.txt'],
            ['test space and + and #.txt'],
            [u'文件.txt']
        )

    def files_content():
        return (
            ['test.txt', b'Hello world!', 'subdir'],
            ['test space and + and #.txt', b'Hello space with+plus#hash!', 'subdir with space + plus and #hash'],
            [u'文件.txt', u'你好世界'.encode('utf-8'), u'文件夹']
        )

    def setUp(self):
        self.temp_dir = tempfile.gettempdir() + '/pyocclient_test%s-%s/' % (int(time.time()), random.randint(1, 1000))
        os.mkdir(self.temp_dir)

        self.client = owncloud.Client(Config['owncloud_url'], dav_endpoint_version=self.get_dav_endpoint_version())
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])
        self.test_root = Config['test_root']
        if not self.test_root[-1] == '/':
            self.test_root += '/'
        if not self.test_root[0] == '/':
            self.test_root = '/' + self.test_root
        self.client.mkdir(self.test_root)
        self.share2user = Config['owncloud_share2user']
        self.share2userPwd = 'Avcpwd4l!'
        self.test_group = Config['test_group']
        try:
            self.client.create_user(self.share2user, self.share2userPwd)
        except:
            pass
        try:
            self.client.create_group(self.test_group)
        except:
            pass

    def tearDown(self):
        self.client.delete(self.test_root)
        try:
            self.client.delete_user(self.share2user)
        except:
            pass
        try:
            self.client.delete_group(self.test_group)
        except:
            pass
        self.client.logout()
        shutil.rmtree(self.temp_dir)

    @staticmethod
    def __create_file(target_file, size):
        file_handle = open(target_file, 'w')
        dummy_data = ''
        for i in range(0, 1024):
            dummy_data += 'X'

        for i in range(0, int(size / 1024)):
            # write in 1kb blocks
            file_handle.write(dummy_data)

        dummy_data = ''
        for i in range(0, size % 1024):
            dummy_data += 'X'

        if (len(dummy_data) > 0):
            file_handle.write(dummy_data)

        file_handle.close()

    @data_provider(files_content)
    def test_mkdir(self, file_name, content, subdir):
        """Test subdirectory creation"""
        self.assertTrue(self.client.mkdir(self.test_root + subdir))
        self.assertIsNotNone(self.client.file_info(self.test_root + subdir))

    @data_provider(files_content)
    def test_put_file_contents(self, file_name, content, subdir):
        """Test creating remote file with given contents"""
        self.assertTrue(self.client.mkdir(self.test_root + subdir))
        self.assertTrue(self.client.put_file_contents(self.test_root + subdir + '/' + file_name, content))

    @data_provider(files_content)
    def test_get_file_contents(self, file_name, content, subdir):
        """Test reading remote file"""
        self.assertTrue(self.client.mkdir(self.test_root + subdir))
        self.assertTrue(self.client.put_file_contents(self.test_root + subdir + '/' + file_name, content))
        self.assertEqual(self.client.get_file_contents(self.test_root + subdir + '/' + file_name), content)

    @data_provider(files_content)
    def test_get_file_info(self, file_name, content, subdir):
        """Test getting file info"""
        self.assertTrue(self.client.mkdir(self.test_root + subdir))
        self.assertTrue(self.client.put_file_contents(self.test_root + file_name, content))

        file_info = self.client.file_info(self.test_root + file_name)
        self.assertTrue(isinstance(file_info, owncloud.FileInfo))
        self.assertEqual(file_info.get_name(), file_name)
        self.assertEqual(file_info.get_path() + '/', self.test_root)
        self.assertEqual(file_info.get_size(), len(content))
        self.assertIsNotNone(file_info.get_etag())
        self.assertEqual(file_info.get_content_type(), 'text/plain')
        self.assertTrue(type(file_info.get_last_modified()) is datetime.datetime)
        self.assertFalse(file_info.is_dir())

        dir_info = self.client.file_info(self.test_root + subdir)
        self.assertTrue(isinstance(dir_info, owncloud.FileInfo))
        self.assertEqual(dir_info.get_name(), subdir)
        self.assertEqual(file_info.get_path() + '/', self.test_root)
        self.assertIsNone(dir_info.get_size())
        self.assertIsNotNone(dir_info.get_etag())
        self.assertEqual(dir_info.get_content_type(), 'httpd/unix-directory')
        self.assertTrue(type(dir_info.get_last_modified()) is datetime.datetime)
        self.assertTrue(dir_info.is_dir())

    def test_get_file_info_non_existing(self):
        """Test getting file info for non existing file"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + 'unexist')
        self.assertEqual(e.exception.status_code, 404)

    def test_get_file_listing(self):
        """Test getting file listing"""
        self.assertTrue(self.client.put_file_contents(self.test_root + 'file one.txt', 'first file'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'zz+z.txt', 'z file'))
        self.assertTrue(self.client.put_file_contents(self.test_root + u'中文.txt', ''))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'abc.txt', ''))
        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'subdir/in dir.txt', ''))

        listing = self.client.list(self.test_root)
        self.assertEqual(len(listing), 5)
        self.assertEqual(listing[0].get_name(), 'abc.txt')
        self.assertEqual(listing[1].get_name(), 'file one.txt')
        self.assertEqual(listing[2].get_name(), 'subdir')
        self.assertEqual(listing[3].get_name(), 'zz+z.txt')
        self.assertEqual(listing[4].get_name(), u'中文.txt')

        self.assertTrue(listing[2].is_dir())
        self.assertFalse(listing[3].is_dir())

        listing = self.client.list(self.test_root, depth="infinity")
        self.assertEqual(len(listing), 6)
        self.assertEqual(listing[2].get_name(), 'subdir')
        self.assertEqual(listing[3].get_name(), 'in dir.txt')

        listing = self.client.list(self.test_root, depth=2)
        self.assertEqual(len(listing), 6)
        self.assertEqual(listing[2].get_name(), 'subdir')
        self.assertEqual(listing[3].get_name(), 'in dir.txt')

    def test_get_file_listing_non_existing(self):
        """Test getting file listing for non existing directory"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.list(self.test_root + 'unexist')
        self.assertEqual(e.exception.status_code, 404)

    @data_provider(files)
    def test_upload_small_file(self, file_name):
        """Test simple upload"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 2 * 1024)
        self.assertTrue(self.client.put_file(self.test_root + file_name, temp_file, chunked=False))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.test_root + file_name)
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.get_size(), 2 * 1024)

    def test_upload_two_chunks(self):
        """Test chunked upload with two chunks"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 18 * 1024 * 1024 + 1)
        self.assertTrue(self.client.put_file(self.test_root + 'chunk_test.dat', temp_file))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.test_root + 'chunk_test.dat')

        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.get_size(), 18 * 1024 * 1024 + 1)

    def test_upload_chunks_minus_one_byte(self):
        """Test chunked upload minus one byte"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 2 * 1024 - 1)
        self.assertTrue(self.client.put_file(self.test_root + 'chunk_test.dat', temp_file, chunk_size = 1024))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.test_root + 'chunk_test.dat')

        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.get_size(), 2 * 1024 - 1)

    @data_provider(files)
    def test_upload_big_file(self, file_name):
        """Test chunked upload"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 22 * 1024 * 1024)
        self.assertTrue(self.client.put_file(self.test_root + file_name, temp_file))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.test_root + file_name)
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.get_size(), 22 * 1024 * 1024)

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
        self.__create_file(temp_dir + u'levelone/文件.dat', 7 * 1024 * 1024)

        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_directory(self.test_root + 'subdir', temp_dir))

        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/file1.dat'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/file2.dat'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/levelone/file3.dat'))
        self.assertIsNotNone(self.client.file_info(self.test_root + 'subdir/pyoctest.dir/levelone/leveltwo/file4.dat'))
        self.assertIsNotNone(self.client.file_info(self.test_root + u'subdir/pyoctest.dir/levelone/文件.dat'))

    @data_provider(files_content)
    def test_download_file(self, file_name, content, subdir):
        """Test file download"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.assertTrue(self.client.mkdir(self.test_root + subdir))
        self.assertTrue(self.client.put_file_contents(self.test_root + subdir + '/' + file_name, content))

        self.assertTrue(self.client.get_file(self.test_root + subdir + '/' + file_name, temp_file))

        f = open(temp_file, 'rb')
        s = f.read()
        f.close()
        os.unlink(temp_file)
        self.assertEqual(s, content)

    def test_download_dir(self):
        import zipfile
        """Test directory download as zip"""
        self.assertTrue(self.client.mkdir(self.test_root + 'subdir'))
        self.assertTrue(self.client.put_file_contents(self.test_root + 'subdir/test.txt', 'hello world!'))
        # Note: this can only work properly with OC 7
        #self.assertTrue(self.client.put_file_contents(self.test_root + 'subdir/文件.txt', '你好世界!'))

        temp_file = self.temp_dir + 'pyoctest.zip'
        self.assertTrue(self.client.get_directory_as_zip(self.test_root, temp_file))

        self.assertTrue(os.stat(temp_file))

        zip_info = zipfile.ZipFile(temp_file)
        listing = zip_info.namelist()

        self.assertEqual(len(listing), 3)
        os.unlink(temp_file)

    @data_provider(files_content)
    def test_delete_file(self, file_name, content, subdir):
        """Test file deletion"""
        self.assertTrue(self.client.mkdir(self.test_root + subdir))
        self.assertTrue(self.client.put_file_contents(self.test_root + subdir + '/' + file_name, content))
        self.assertTrue(self.client.delete(self.test_root + subdir + '/' + file_name))
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + subdir + '/' + file_name)
        self.assertEqual(e.exception.status_code, 404)

    @data_provider(files_content)
    def test_delete_dir(self, file_name, content, subdir):
        """Test directory deletion"""
        self.assertTrue(self.client.mkdir(self.test_root + subdir))
        self.assertTrue(self.client.put_file_contents(self.test_root + subdir + '/' + file_name, content))
        self.assertTrue(self.client.delete(self.test_root + subdir))
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + subdir + '/' + file_name)
        self.assertEqual(e.exception.status_code, 404)
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.file_info(self.test_root + subdir)
        self.assertEqual(e.exception.status_code, 404)

    def test_move_rename_in_place(self):
        """Test rename in place"""

        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'rename this file!.txt',
                'to rename'
            )
        )
        self.assertTrue(
            self.client.move(
                self.test_root + 'rename this file!.txt',
                self.test_root + 'renamed in place.txt'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'renamed in place.txt'
            ),
            b'to rename'
        )

    def test_move_and_rename(self):
        """Test rename into subdir"""

        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'move and rename.txt',
                'first file'
            )
        )
        self.assertTrue(
            self.client.mkdir(
                self.test_root + 'subdir'
            )
        )
        self.assertTrue(
            self.client.move(
                self.test_root + 'move and rename.txt',
                self.test_root + 'subdir/file renamed.txt'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'subdir/file renamed.txt'
            ),
            b'first file'
        )

    def test_move_to_dir(self):
        """Test move into directory"""

        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'movetodir.txt',
                'z file'
            )
        )
        # move to subdir
        self.assertTrue(
            self.client.mkdir(
                self.test_root + 'subdir'
            )
        )
        self.assertTrue(
            self.client.move(
                self.test_root + 'movetodir.txt',
                self.test_root + 'subdir/'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'subdir/movetodir.txt'
            ),
            b'z file'
        )

    def test_move_subdir(self):
        """Test move subdir"""

        # subdir to move
        self.assertTrue(
            self.client.mkdir(
                self.test_root + 'subdir_to_move'
            )
        )
        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'subdir_to_move/file two.txt',
                'second file'
            )
        )
        self.assertTrue(
            self.client.mkdir(
                self.test_root + 'subdir'
            )
        )
        self.assertTrue(
            self.client.move(
                self.test_root + 'subdir_to_move',
                self.test_root + 'subdir/'
            )
        )

    def test_rename_unicode(self):
        """Test rename unicode"""

        # rename
        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + u'中文.txt',
                '1'
            )
        )
        self.assertTrue(
            self.client.move(
                self.test_root + u'中文.txt',
                self.test_root + u'更多中文.txt'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + u'更多中文.txt'
            ),
            b'1'
        )

    def test_move_unicode(self):
        """Test move unicode to dir"""
        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + u'中文.txt',
                '2'
            )
        )
        self.assertTrue(
            self.client.mkdir(
                self.test_root + 'subdir'
            )
        )
        self.assertTrue(
            self.client.move(
                self.test_root + u'中文.txt',
                self.test_root + u'subdir/中文.txt'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + u'subdir/中文.txt'
            ),
            b'2'
        )

    def test_move_to_non_existing_dir(self):
        """Test error when moving to non existing dir"""

        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'move not possible.txt',
                'x'
            )
        )
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.move(
                self.test_root + 'move not possible.txt',
                self.test_root + 'non-existing-dir/subdir/x.txt'
            )
        self.assertEqual(e.exception.status_code, 409)

        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'move not possible.txt'
            ),
            b'x'
        )

    def test_copy_in_place(self):
        """Test copy in place"""

        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'copy this file!.txt',
                'to copy'
            )
        )
        self.assertTrue(
            self.client.copy(
                self.test_root + 'copy this file!.txt',
                self.test_root + 'copied in place.txt'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'copied in place.txt'
            ),
            b'to copy'
        )

        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'copy this file!.txt'
            ),
            b'to copy'
        )

    def test_copy_into_subdir(self):
        """Test copy into subdir"""

        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'copy into subdir.txt',
                'first file'
            )
        )
        self.assertTrue(
            self.client.mkdir(
                self.test_root + 'subdir'
            )
        )
        self.assertTrue(
            self.client.copy(
                self.test_root + 'copy into subdir.txt',
                self.test_root + 'subdir/file copied.txt'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'subdir/file copied.txt'
            ),
            b'first file'
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'copy into subdir.txt'
            ),
            b'first file'
        )

    def test_copy_unicode(self):
        """Test copy unicode to dir"""
        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + u'दिलै होस छोरा होस.txt',
                'content'
            )
        )
        self.assertTrue(
            self.client.mkdir(
                self.test_root + 'subdir'
            )
        )
        self.assertTrue(
            self.client.copy(
                self.test_root + u'दिलै होस छोरा होस.txt',
                self.test_root + u'subdir/दिलै होस छोरा होस.txt'
            )
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + u'subdir/दिलै होस छोरा होस.txt'
            ),
            b'content'
        )
        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + u'दिलै होस छोरा होस.txt'
            ),
            b'content'
        )

    def test_copy_to_non_existing_dir(self):
        """Test error when copy to non existing dir"""

        self.assertTrue(
            self.client.put_file_contents(
                self.test_root + 'copy not possible.txt',
                'x'
            )
        )
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.copy(
                self.test_root + 'copy not possible.txt',
                self.test_root + 'non-existing-dir/subdir/x.txt'
            )
        self.assertEqual(e.exception.status_code, 409)

        self.assertEqual(
            self.client.get_file_contents(
                self.test_root + 'copy not possible.txt'
            ),
            b'x'
        )

    @data_provider(files)
    def test_share_with_link(self, file_name):
        """Test sharing a file with link"""

        path = self.test_root + file_name
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        share_info = self.client.share_file_with_link(path, public_upload=False, password='AnvvsP1234', name='Test Link')

        self.assertTrue(self.client.is_shared(path))
        self.assertTrue(isinstance(share_info, owncloud.ShareInfo))
        self.assertTrue(type(share_info.get_id()) is int)
        self.assertEqual(share_info.get_path(), path)
        self.assertEqual(share_info.get_name(), 'Test Link')
        self.assertTrue(type(share_info.get_link()) is str)
        self.assertTrue(type(share_info.get_token()) is str)

    def test_share_with_link_non_existing_file(self):
        """Test sharing a file with link"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.share_file_with_link(self.test_root + 'unexist.txt')
        self.assertEqual(e.exception.status_code, 404)

    @data_provider(files)
    def test_share_with_user(self, file_name):
        """Test sharing a file to user"""

        path = self.test_root + file_name
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        share_info = self.client.share_file_with_user(path, self.share2user)

        self.assertTrue(self.client.is_shared(path))
        self.assertTrue(isinstance(share_info, owncloud.ShareInfo))
        self.assertEqual(share_info.get_path(), path)
        self.assertTrue(type(share_info.get_id()) is int)
        self.assertEqual(share_info.get_permissions(), 1)

        shareclient = owncloud.Client(Config['owncloud_url'])
        shareclient.login(self.share2user, self.share2userPwd)
        share2_info = shareclient.get_shares(
            "/", shared_with_me=True)[0].share_info
        self.assertEqual(share2_info["uid_owner"], Config['owncloud_login'])
        self.assertEqual(file_name, share2_info["file_target"][1:])
        shareclient.logout()

        self.assertTrue(self.client.delete(path))

    @data_provider(files)
    def test_share_with_group(self, file_name):
        """Test sharing a file to a group"""

        path = self.test_root + file_name
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        share_info = self.client.share_file_with_group(path, self.test_group, perms=31)

        self.assertTrue(self.client.is_shared(path))
        self.assertTrue(isinstance(share_info, owncloud.ShareInfo))
        self.assertEqual(share_info.get_path(), path)
        self.assertTrue(type(share_info.get_id()) is int)
        self.assertEqual(share_info.get_permissions(), 31)
        self.assertTrue(self.client.delete(path))

    @data_provider(files)
    def test_delete_share(self, file_name):
        """Test deleting a share (by id)"""

        path = self.test_root + file_name
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        share_info = self.client.share_file_with_user(path, self.share2user)

        self.assertTrue(self.client.is_shared(path))
        self.assertIsNotNone(self.client.delete_share(share_info.get_id()))
        self.assertFalse(self.client.is_shared(path))

    def test_is_shared_non_existing_path(self):
        """Test is_shared - path does not exist"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.is_shared(self.test_root + 'does_not_exist')
        self.assertEqual(e.exception.status_code, 404)

    def test_is_shared_not_shared_path(self):
        """Test is_shared - path does exist, but it's not shared yet"""
        path = self.test_root + 'not_shared_path.txt'
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))
        self.assertFalse(self.client.is_shared(path))

    @data_provider(files)
    def test_is_shared(self, file_name):
        """Test is_shared"""
        path = self.test_root + file_name
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        self.client.share_file_with_link(path)
        self.assertTrue(self.client.is_shared(path))
        self.assertTrue(self.client.delete(path))

    @data_provider(files)
    def test_get_share_user(self, file_name):
        """Test get_share() for user share"""
        path = self.test_root + file_name
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        sinfo_run = self.client.share_file_with_user(
            path,
            self.share2user,
            perms=self.client.OCS_PERMISSION_READ | self.client.OCS_PERMISSION_SHARE
        )
        sinfo = self.client.get_share(sinfo_run.get_id())
        self.assertIsInstance(sinfo, owncloud.ShareInfo)
        share_id = sinfo.get_id()
        self.assertGreater(share_id, 0)
        self.assertEqual(sinfo_run.get_id(), share_id)
        self.assertIsInstance(sinfo.get_id(), int)
        self.assertEqual(sinfo.get_share_type(), self.client.OCS_SHARE_TYPE_USER)
        self.assertEqual(sinfo.get_share_with(), self.share2user)
        self.assertEqual(sinfo.get_path(), path)
        self.assertEqual(
            sinfo.get_permissions(),
            self.client.OCS_PERMISSION_READ | self.client.OCS_PERMISSION_SHARE
        )
        self.assertIsInstance(sinfo.get_share_time(), datetime.datetime)
        self.assertIsNone(sinfo.get_expiration())
        self.assertIsNone(sinfo.get_token())
        self.assertEqual(sinfo.get_uid_owner(), Config['owncloud_login'])
        self.assertIsInstance(sinfo.get_displayname_owner(), six.string_types)

    @data_provider(files)
    def test_get_share_public_link(self, file_name):
        """Test get_share() for public link share"""
        path = self.test_root + file_name
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        sinfo_run = self.client.share_file_with_link(path)
        sinfo = self.client.get_share(sinfo_run.get_id())
        self.assertIsInstance(sinfo, owncloud.ShareInfo)
        self.assertIsNotNone(sinfo)
        share_id = sinfo.get_id()
        self.assertGreater(share_id, 0)
        self.assertEqual(sinfo_run.get_id(), share_id)
        self.assertIsInstance(sinfo.get_id(), int)
        self.assertEqual(sinfo.get_share_type(), self.client.OCS_SHARE_TYPE_LINK)
        self.assertIsNone(sinfo.get_share_with())
        self.assertEqual(sinfo.get_path(), path)
        self.assertEqual(sinfo.get_permissions(), self.client.OCS_PERMISSION_READ)
        self.assertIsInstance(sinfo.get_share_time(), datetime.datetime)
        self.assertIsNone(sinfo.get_expiration())
        self.assertIsInstance(sinfo.get_token(), six.string_types)
        self.assertEqual(sinfo.get_uid_owner(), Config['owncloud_login'])
        self.assertIsInstance(sinfo.get_displayname_owner(), six.string_types)

    def test_get_share_non_existing(self):
        """Test get_share - share with specified id does not exist"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.get_share(-1)
        self.assertEqual(e.exception.status_code, 404)

    def test_get_shares_non_existing_path(self):
        """Test get_shares - path does not exist"""
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.get_shares(self.test_root + 'does_not_exist')
        self.assertEqual(e.exception.status_code, 404)

    @data_provider(files)
    def test_get_shares(self, file_name):
        """Test get_shares"""
        self.assertTrue(self.client.put_file_contents(self.test_root + file_name, 'hello world!'))

        self.client.share_file_with_link(self.test_root + file_name)
        shares = self.client.get_shares(self.test_root + file_name)
        self.assertIsNotNone(shares)
        self.assertIsInstance(shares, list)

        shares = None
        with self.assertRaises(owncloud.ResponseError) as e:
            shares = self.client.get_shares(self.test_root + file_name, subfiles=True)
        self.assertIsNone(shares)
        self.assertEqual(e.exception.status_code, 400)

        shares = self.client.get_shares(self.test_root, reshares=True, subfiles=True)
        self.assertIsNotNone(shares)
        self.assertIsInstance(shares, list)
        self.assertGreater(len(shares), 0)

        self.assertTrue(self.client.put_file_contents(self.test_root + file_name + '2.txt', 'hello world!'))
        self.client.share_file_with_link(self.test_root + file_name + '2.txt')
        shares = self.client.get_shares(self.test_root, reshares=True, subfiles=True)
        self.assertIsNotNone(shares)
        self.assertIsInstance(shares, list)
        self.assertGreater(len(shares), 1)

    def test_get_shares_empty(self):
        """Test get shares with empty result"""
        file_name = 'test.txt'
        self.assertTrue(self.client.put_file_contents(self.test_root + file_name, 'hello world!'))

        # Get all shares
        shares = self.client.get_shares()
        self.assertEqual(shares, [])

    def test_update_share_wo_params(self):
        self.assertFalse(self.client.update_share(0))

    def test_update_share_user(self):
        """Test updating a share parameters - user share"""
        path = self.test_root + 'update_share_user.txt'
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        share_info = self.client.share_file_with_user(path, self.share2user)
        share_id = share_info.get_id()
        maxPerms = self.client.OCS_PERMISSION_READ + self.client.OCS_PERMISSION_UPDATE + self.client.OCS_PERMISSION_SHARE
        self.assertTrue(self.client.update_share(share_id, perms=maxPerms))
        perms = self.client.get_shares(path)[0].get_permissions()
        # now the permissions should be OCS_PERMISSION_ALL,
        # because we've shared it with a user
        self.assertEqual(int(perms), maxPerms)
        self.assertTrue(self.client.delete_share(share_id))

    def test_update_share_public(self):
        """Test updating a share parameters - public share"""
        path = self.test_root + 'update_share_public.txt'
        self.assertTrue(self.client.put_file_contents(path, 'hello world!'))

        share_info = self.client.share_file_with_link(path)
        share_id = share_info.get_id()
        self.assertTrue(self.client.update_share(share_id, perms=self.client.OCS_PERMISSION_ALL))
        perms = self.client.get_shares(path)[0].get_permissions()
        # permissions should still be OCS_PERMISSION_READ not OCS_PERMISSION_ALL,
        # because it's a public share
        self.assertEqual(int(perms), self.client.OCS_PERMISSION_READ)
        self.assertTrue(self.client.delete_share(share_id))

    def test_update_share_public_upload(self):
        """Test updating a share parameters - public upload"""
        path = self.test_root + 'update_share_public_upload'
        self.client.mkdir(path)

        share_info = self.client.share_file_with_link(path)
        share_id = share_info.get_id()
        self.assertTrue(self.client.update_share(share_id, public_upload=True))
        perms = self.client.get_shares(path)[0].get_permissions()

        # make sure the server did receive the upload permission
        self.assertTrue(perms & self.client.OCS_PERMISSION_CREATE > 0)
        self.assertTrue(perms & self.client.OCS_PERMISSION_UPDATE > 0)

        # test reverting to read only
        self.assertTrue(self.client.update_share(share_id, public_upload=False))
        perms = self.client.get_shares(path)[0].get_permissions()
        self.assertEqual(int(perms), self.client.OCS_PERMISSION_READ)
        self.assertTrue(self.client.delete_share(share_id))

    def test_update_share_password(self):
        """Test updating a share parameters - password"""
        path = self.test_root + 'update_share_password'
        self.client.mkdir(path)

        share_info = self.client.share_file_with_link(path)
        share_id = share_info.get_id()
        self.assertTrue(self.client.update_share(share_id, password="2hard2guess"))
        share_info = self.client.get_shares(path)[0]
        self.assertTrue(type(share_info.get_share_with_displayname()) is str)
        self.assertTrue(self.client.delete_share(share_id))

@skipIfDavVersionLessThan(1.0)
class TestFileAccessDav1(TestFileAccess):
    def get_dav_endpoint_version(self):
        return 1

class TestPrivateDataAccess(unittest.TestCase):

    def attrs():
        return (
            ('attr1', 'value1'),
            ('attr+plus space', 'value+plus space and/slash'),
            (u'属性1', u'值对1')
        )

    def setUp(self):
        self.client = owncloud.Client(Config['owncloud_url'])
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])
        self.app_name = Config['app_name']

    def tearDown(self):
        # TODO: delete all attributes ?
        self.client.logout()

    @data_provider(attrs)
    def test_set_attribute(self, attr1, value1):
        """Test setting an attribute"""
        self.assertTrue(self.client.set_attribute(self.app_name, attr1, value1))
        self.assertTrue(self.client.delete_attribute(self.app_name, attr1))

    @data_provider(attrs)
    def test_get_attribute(self, attr1, value1):
        """Test getting an attribute"""
        self.assertTrue(self.client.set_attribute(self.app_name, attr1, value1))

        self.assertEqual(self.client.get_attribute(self.app_name, attr1), value1)
        self.assertEqual(self.client.get_attribute(self.app_name), [(attr1, value1)])
        self.assertTrue(self.client.delete_attribute(self.app_name, attr1))

    def test_get_non_existing_attribute(self):
        """Test getting the value of a non existing attribute"""
        self.assertIsNone(self.client.get_attribute(self.app_name, 'unexist'))

    @data_provider(attrs)
    def test_set_attribute_empty(self, attr1, value1):
        """Test setting an attribute to an empty value"""
        self.assertTrue(self.client.set_attribute(self.app_name, attr1, ''))
        self.assertEqual(self.client.get_attribute(self.app_name, attr1), '')
        self.assertEqual(self.client.get_attribute(self.app_name), [(attr1, '')])
        self.assertTrue(self.client.delete_attribute(self.app_name, attr1))

    @data_provider(attrs)
    def test_delete_attribute(self, attr1, value1):
        """Test deleting an attribute"""
        self.assertTrue(self.client.set_attribute(self.app_name, attr1, value1))
        self.assertEqual(self.client.get_attribute(self.app_name, attr1), value1)

        self.assertTrue(self.client.delete_attribute(self.app_name, attr1))

        self.assertIsNone(self.client.get_attribute(self.app_name, attr1))
        self.assertEqual(self.client.get_attribute(self.app_name), [])


class TestUserAndGroupActions(unittest.TestCase):

    def setUp(self):
        self.client = owncloud.Client(Config['owncloud_url'])
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])
        self.groups_to_create = Config['groups_to_create']
        self.not_existing_group = Config['not_existing_group']
        self.test_group = Config['test_group']
        self.share2user = Config['owncloud_share2user']
        self.share2userPwd = 'Avcpwd4l!'
        try:
            self.apps = self.client.get_apps()
            if not self.apps['provisioning_api']:
                raise unittest.SkipTest("no API")
        except owncloud.ResponseError:
            raise unittest.SkipTest("no API")

        try:
            self.client.create_user(self.share2user, self.share2userPwd)
        except:
            pass
        try:
            self.client.create_group(self.test_group)
        except:
            pass

    def tearDown(self):
        for group in self.groups_to_create:
            self.assertTrue(self.client.delete_group(group))

        self.assertTrue(self.client.remove_user_from_group(self.share2user,self.test_group))
        try:
            self.client.delete_user(self.share2user)
        except:
            pass
        try:
            self.client.delete_group(self.test_group)
        except:
            pass

        self.client.logout()

    def test_user_exists(self):
        self.assertTrue(self.client.user_exists(Config['owncloud_login']))
        try:
            self.client.create_user('ghost_user', 'ghost_pass')
            self.client.delete_user('ghost_user')
            self.assertFalse(self.client.user_exists('ghost_user'))
        except:
            pass

    def test_get_user(self):
        output = self.client.get_user(Config['owncloud_login'])
        expected_output =   {'displayname': 'admin',
                             'enabled': 'true',
                             'email': None,
                             'quota': {'total': '309355267452',
                                       'relative': '0',
                                       'used': '3261820',
                                       'free': '309352005632'}
                            }
        self.assertEqual(output['displayname'], expected_output['displayname'])
        self.assertEqual(output['enabled'], expected_output['enabled'])
        self.assertEqual(output['email'], expected_output['email'])
        self.assertTrue('total' in output['quota'])
        self.assertTrue('relative' in output['quota'])
        self.assertTrue('used' in output['quota'])
        self.assertTrue('free' in output['quota'])

    def test_search_users(self):
        user_name = Config['owncloud_login']
        users = self.client.search_users(user_name[:-1])
        self.assertIn(user_name, users)

    def test_get_users(self):
        user_name = Config['owncloud_login']
        users = self.client.get_users()
        self.assertIn(user_name, users)

    def test_set_user_attribute(self):
        try:
            self.client.create_user('ghost_user', 'ghost_pass')
        except:
            self.client.delete_user('ghost_user')
            self.client.create_user('ghost_user', 'ghost_pass')
        self.assertTrue(self.client.set_user_attribute('ghost_user','email','test@inf.org'))
        self.assertTrue(self.client.set_user_attribute('ghost_user','password','secret7363*'))
        self.assertEqual(self.client.get_user('ghost_user')['email'], 'test@inf.org')
        self.client.delete_user('ghost_user')

        with self.assertRaises(owncloud.OCSResponseError) as e:
            self.client.set_user_attribute(self.share2user,'email',"äöüää_sfsdf+$%/)%&=")
        self.assertEqual(e.exception.status_code, 102)
        #try to catch with general ResponseError
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.set_user_attribute(self.share2user,'email',"äöüää_sfsdf+$%/)%&=")
        self.assertEqual(e.exception.status_code, 102)

    def test_create_existing_user(self):
        with self.assertRaises(owncloud.OCSResponseError) as e:
            self.client.create_user(self.share2user, self.share2userPwd)
        self.assertEqual(e.exception.status_code, 102)
        # try to catch with general ResponseError
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.create_user(self.share2user, self.share2userPwd)
        self.assertEqual(e.exception.status_code, 102)

    def test_create_groups(self):
        for group in self.groups_to_create:
            self.assertTrue(self.client.create_group(group))
            self.assertTrue(self.client.group_exists(group))
            # try to create them again, that should raise and OCSResponseError with code 102
            with self.assertRaises(owncloud.OCSResponseError) as e:
                self.client.create_group(group)
            self.assertEqual(e.exception.status_code, 102)
            #try to catch with general ResponseError
            with self.assertRaises(owncloud.ResponseError) as e:
                self.client.create_group(group)
            self.assertEqual(e.exception.status_code, 102)

    def test_get_groups(self):
        test_group = Config['test_group']
        not_existing_group = Config['not_existing_group']
        groups = self.client.get_groups()
        self.assertIn(test_group, groups)
        self.assertNotIn(not_existing_group, groups)

    def test_get_group_members(self):
        user_name = Config['owncloud_login']
        test_group = Config['test_group']
        admin_members = self.client.get_group_members('admin')
        test_members = self.client.get_group_members(test_group)
        self.assertIn(user_name, admin_members)
        self.assertNotIn(user_name, test_members)

    def test_not_existing_group(self):
        self.assertFalse(self.client.group_exists(self.not_existing_group))

    def test_add_user_to_group_remove_user_from_group(self):
        self.assertFalse(self.client.user_is_in_group(self.share2user,self.test_group))
        self.assertTrue(self.client.add_user_to_group(self.share2user,self.test_group))
        self.assertTrue(self.client.user_is_in_group(self.share2user,self.test_group))

        # try to add the user to a not existing group, that should raise and OCSResponseError with code 102
        with self.assertRaises(owncloud.OCSResponseError) as e:
            self.client.add_user_to_group(self.share2user,self.not_existing_group)
        self.assertEqual(e.exception.status_code, 102)
        # try to catch with general ResponseError
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.add_user_to_group(self.share2user,self.not_existing_group)
        self.assertEqual(e.exception.status_code, 102)

        self.assertTrue(self.client.remove_user_from_group(self.share2user,self.test_group))
        self.assertFalse(self.client.user_is_in_group(self.share2user,self.test_group))

        # try to remove the user from a not existing group, that should raise and OCSResponseError with code 102
        with self.assertRaises(owncloud.OCSResponseError) as e:
            self.client.remove_user_from_group(self.share2user,self.not_existing_group)
        self.assertEqual(e.exception.status_code, 102)
        # try to catch with general ResponseError
        with self.assertRaises(owncloud.ResponseError) as e:
            self.client.remove_user_from_group(self.share2user,self.not_existing_group)
        self.assertEqual(e.exception.status_code, 102)

        # try to remove user without giving group name
        with self.assertRaises(owncloud.OCSResponseError) as e:
            self.client.remove_user_from_group(self.share2user,'')
        self.assertEqual(e.exception.status_code, 101)

        # try to remove not existing user from a group
        with self.assertRaises(owncloud.OCSResponseError) as e:
            self.client.remove_user_from_group("iGuessThisUserNameDoesNotExistInTheSystem",self.test_group)
        self.assertEqual(e.exception.status_code, 103)


class TestApps(unittest.TestCase):

    def setUp(self):
        self.client = owncloud.Client(Config['owncloud_url'])
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])

    def test_enable_app_disable_app(self):
        self.assertTrue(self.client.enable_app('activity'))
        self.assertTrue(self.client.disable_app('activity'))

    def tearDown(self):
        self.client.logout()


class TestGetConfig(unittest.TestCase):

    def setUp(self):
        self.client = owncloud.Client(Config['owncloud_url'])
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])

    def test_get_config(self):
        """Test get_config() function"""
        self.assertIsNotNone(self.client.get_config())

    def test_get_version(self):
        """Test get_version() function"""
        version = self.client.get_version()
        self.assertIsNotNone(version)
        version_parts = version.split('.')
        self.assertGreaterEqual(int(version_parts[0]), 5)

    def test_get_capabilities(self):
        """Test get_capabilities() function"""
        caps = self.client.get_capabilities()
        # files app is always enabled
        self.assertIsNotNone(caps['files'])
        # and always has big file chunking enabled
        self.assertEqual(caps['files']['bigfilechunking'], '1')

    def tearDown(self):
        self.client.logout()


class TestLogin(unittest.TestCase):

    def setUp(self):
        self.client = owncloud.Client(Config['owncloud_url'])

    def test_login(self):
        with self.assertRaises(owncloud.HTTPResponseError) as e:
            self.client.login("iGuessThisUserNameDoesNotExistInTheSystem","iGuessThisUserNameDoesNotExistInTheSystem")
        self.assertEqual(e.exception.status_code, 401)
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])

    def tearDown(self):
        self.client.logout()


class TestOCSRequest(unittest.TestCase):

    def setUp(self):
        self.client = owncloud.Client(Config['owncloud_url'])
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])

    def test_make_request(self):
        kwargs = {
            'accepted_codes': [100]
        }
        self.client.make_ocs_request(
            'GET',
            '',
            'config',
            **kwargs
        )

    def test_make_request_fail_unaccepted_code(self):
        kwargs = {
            'accepted_codes': [102]
        }
        with self.assertRaises(owncloud.OCSResponseError) as e:
            self.client.make_ocs_request(
                'GET',
                '',
                'config',
                **kwargs
            )
        self.assertEqual(e.exception.status_code, 100)

    def tearDown(self):
        self.client.logout()

class TestPublicFolder(unittest.TestCase):

    def get_dav_endpoint_version(self):
        return 0

    def files():
        return (
            ['test.txt'],
            ['test space and + and #.txt'],
            [u'文件.txt']
        )

    def files_content():
        return (
            ['test.txt', b'Hello world!', 'subdir'],
            ['test space and + and #.txt', b'Hello space with+plus#hash!', 'subdir with space + plus and #hash'],
            [u'文件.txt', u'你好世界'.encode('utf-8'), u'文件夹']
        )

    
    def setUp(self):
        self.temp_dir = tempfile.gettempdir() + '/pyocclient_test%s-%s/' % (int(time.time()), random.randint(1, 1000))
        os.mkdir(self.temp_dir)

        self.client = owncloud.Client(Config['owncloud_url'], dav_endpoint_version=self.get_dav_endpoint_version())
        self.client.login(Config['owncloud_login'], Config['owncloud_password'])
        self.test_root = Config['test_root']
        if not self.test_root[-1] == '/':
            self.test_root += '/'
        if not self.test_root[0] == '/':
            self.test_root = '/' + self.test_root

        # setting up the root dir
        self.client.mkdir(self.test_root)
        self.download_testfile = 'download_pyoctest.dat'
        self.upload_testfile = 'upload_pyoctest.dat'
        self.folder_password = 'secret'
        temp_file = self.temp_dir + self.download_testfile

        # create pathing for different scenarios
        self.public_folder_download = self.test_root + 'public_share_download/' # file download only
        self.public_folder_upload = self.test_root + 'public_share_upload/' # file upload only
        self.pw_public_folder_download = self.test_root + 'pw_public_share_download/' # password protected download
        self.pw_public_folder_upload = self.test_root + 'pw_public_share_upload/' # password protected upload

        # make folder with public download only
        self.client.mkdir(self.public_folder_download)
        public_share_info = self.client.share_file_with_link(self.public_folder_download, perms=self.client.OCS_PERMISSION_READ)
        self.public_download_link = public_share_info.get_link()
        self.public_download_token = public_share_info.get_token()

        # populate folder with data
        temp_file = self.temp_dir + self.download_testfile
        self.__create_file(temp_file, 2 * 1024)
        self.client.put_file(self.public_folder_download + self.download_testfile, temp_file, chunked=False)

        # make folder with public upload only
        self.client.mkdir(self.public_folder_upload)
        public_share_info = self.client.share_file_with_link(self.public_folder_upload, perms=self.client.OCS_PERMISSION_CREATE)
        self.public_upload_link = public_share_info.get_link()
        self.public_upload_token = public_share_info.get_token()

        # make password protected folder with public download only
        self.client.mkdir(self.pw_public_folder_download)
        public_share_info = self.client.share_file_with_link(self.pw_public_folder_download, perms=self.client.OCS_PERMISSION_READ, password=self.folder_password)
        self.pw_public_download_link = public_share_info.get_link()
        self.pw_public_download_token = public_share_info.get_token()

        # populate password protected folder with data
        temp_file = self.temp_dir + self.download_testfile
        self.__create_file(temp_file, 2 * 1024)
        self.client.put_file(self.pw_public_folder_download + self.download_testfile, temp_file, chunked=False)

        # make password protected folder with public upload only
        self.client.mkdir(self.pw_public_folder_upload)
        public_share_info = self.client.share_file_with_link(self.pw_public_folder_upload, perms=self.client.OCS_PERMISSION_CREATE, password=self.folder_password)
        self.pw_public_upload_link = public_share_info.get_link()
        self.pw_public_upload_token = public_share_info.get_token()

    def tearDown(self):
        self.client.delete(self.test_root)
        self.client.logout()
        self.anon_client.logout()
        shutil.rmtree(self.temp_dir)

    @staticmethod
    def __create_file(target_file, size):
        file_handle = open(target_file, 'w')
        dummy_data = ''
        for i in range(0, 1024):
            dummy_data += 'X'

        for i in range(0, int(size / 1024)):
            # write in 1kb blocks
            file_handle.write(dummy_data)

        dummy_data = ''
        for i in range(0, size % 1024):
            dummy_data += 'X'

        if (len(dummy_data) > 0):
            file_handle.write(dummy_data)

        file_handle.close()

    def test_anon_login(self):
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.public_download_token)
        listing = self.anon_client.list('/')
        self.assertEqual(len(listing), 1)

        # repeat with wrong token
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login('badtoken')
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 401)

        # repeat with upload only folder (listing not allowed)
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.public_upload_token)
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 404)
    
    def test_anon_login_pw(self):
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.pw_public_download_token, folder_password=self.folder_password)
        listing = self.anon_client.list('/')
        self.assertEqual(len(listing), 1)

        # repeat with wrong password
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.pw_public_download_token, folder_password='wrongpassword')
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 401)

        # repeat with upload only folder (listing not allowed)
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.pw_public_upload_token, folder_password=self.folder_password)
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 404)

    def test_from_link(self):
        self.anon_client = owncloud.Client.from_public_link(self.public_download_link)
        listing = self.anon_client.list('/')
        self.assertEqual(len(listing), 1)

        # repeat with wrong link
        self.anon_client = owncloud.Client.from_public_link(Config['owncloud_url'] + 'index.php/s/wronglink')
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 401)

        # repeat with upload only folder (listing not allowed)
        self.anon_client = owncloud.Client.from_public_link(self.public_upload_link)
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 404)
    
    def test_from_link_pw(self):
        self.anon_client = owncloud.Client.from_public_link(self.pw_public_download_link, folder_password=self.folder_password)
        listing = self.anon_client.list('/')
        self.assertEqual(len(listing), 1)

        # repeat with wrong password
        self.anon_client = owncloud.Client.from_public_link(self.pw_public_download_link, folder_password='wrongpassword')
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 401)

        # repeat with upload only folder (listing not allowed)
        self.anon_client = owncloud.Client.from_public_link(self.pw_public_upload_link, folder_password=self.folder_password)
        with self.assertRaises(owncloud.ResponseError) as e:
            self.anon_client.list('/')
        self.assertEqual(e.exception.status_code, 404)             


    @data_provider(files_content)
    def test_download_file(self, file_name, content, subdir):
        """Test file download"""
        # populate folder with data
        temp_file = self.temp_dir + file_name
        self.client.put_file_contents(self.public_folder_download + '/' + file_name, content)

        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.public_download_token)

        self.assertTrue(self.anon_client.get_file('/' + file_name, temp_file))

        f = open(temp_file, 'rb')
        s = f.read()
        f.close()
        os.unlink(temp_file)
        self.assertEqual(s, content)

    # ZIP Download requires new method for anon session. API URL differs from regular session.
    # def test_download_dir(self, file_name, content, subdir):

    @data_provider(files_content)
    def test_mkdir(self, file_name, content, subdir):
        """Test subdirectory creation"""
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.public_upload_token)

        self.assertTrue(self.anon_client.mkdir(subdir))
        # Only users with account can get file info in upload folders
        self.assertIsNotNone(self.client.file_info(self.public_folder_upload + subdir))
    
    @data_provider(files)
    def test_upload_small_file(self, file_name):
        """Test simple upload"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 2 * 1024)
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.public_upload_token)

        self.assertTrue(self.anon_client.put_file('/' + file_name, temp_file, chunked=False))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.public_folder_upload + file_name)
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.get_size(), 2 * 1024)
    
    @data_provider(files)
    def test_upload_big_file(self, file_name):
        """Test chunked upload"""
        temp_file = self.temp_dir + 'pyoctest.dat'
        self.__create_file(temp_file, 10 * 1024 * 1024)

        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.public_upload_token)

        self.assertTrue(self.anon_client.put_file('/' + file_name, temp_file))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.public_folder_upload + file_name)
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.get_size(), 10 * 1024 * 1024)

    @data_provider(files)
    def test_drop_file(self, file_name):
        """Test convinience wrapper"""
        temp_file = self.temp_dir + file_name
        self.__create_file(temp_file, 2 * 1024)
        self.anon_client = owncloud.Client(Config['owncloud_url'])
        self.anon_client.anon_login(self.public_upload_token)

        self.assertTrue(self.anon_client.drop_file(temp_file))
        os.unlink(temp_file)

        file_info = self.client.file_info(self.public_folder_upload + file_name)
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.get_size(), 2 * 1024)

if __name__ == '__main__':
    unittest.main()
