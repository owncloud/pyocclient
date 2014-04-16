# -*- coding: utf-8 -*-
#
# vim: expandtab shiftwidth=4 softtabstop=4
#

import datetime
import time
import urllib
import urlparse
import requests
import xml.etree.ElementTree as ET
import os

class PublicShare():
    def __init__(self, share_id, target_file, link, token):
        self.share_id = share_id
        self.target_file = target_file
        self.link = link
        self.token = token

    def __str__(self):
        return 'PublicShare(id=%i,path=%s,link=%s,token=%s)' % (self.share_id, self.target_file, self.link, self.token)

class File():
    __DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self, path, file_type = 'file', attributes = {}):
        self.path = path
        self.file_type = file_type
        self.attributes = attributes

    def getSize(self):
        return int(self.attributes['{DAV:}getcontentlength'])

    def getETag(self):
        return self.attributes['{DAV:}getetag']

    def getContentType(self):
        return self.attributes['{DAV:}getcontenttype']

    def getLastModified(self):
        return datetime.datetime.strptime(self.attributes['{DAV:}getlastmodified'], self.__DATE_FORMAT)

    def __str__(self):
        return 'File(path=%s,file_type=%s,attributes=%s)' % (self.path, self.file_type, self.attributes)

    def __repr__(self):
        return self.__str__()

class Client():
    __DEBUG = True

    def __init__(self, url):
        if not url[-1] == '/':
            url = url + '/'

        self.url = url
        self.__auth = None

        url_components = urlparse.urlparse(url)
        self.__davpath = url_components.path + 'remote.php/webdav'
        self.__webdav_url = url + 'remote.php/webdav'
        self.__ocs_share_url = url + 'ocs/v1.php/apps/files_sharing/api/v1/'

    def login(self, user_id, password):
        self.__auth = (user_id, password)
        res = requests.get(self.url, auth = self.__auth)
        if res.status_code == 200:
            self.authenticated = True
            return True
        self.authenticated = False
        return False

    def logout(self):
        # TODO
        pass

    def fileinfo(self, path):
        return self.__makeDAVRequest('PROPFIND', path)

    def get(self, path):
        path = self.__normalizePath(path)
        res = requests.get(self.__webdav_url + path, auth = self.__auth)
        if res.status_code == 200:
            return res.content
        return False

    def getToFile(self, path, target_file = None):
        path = self.__normalizePath(path)
        res = requests.get(self.__webdav_url + path, auth = self.__auth, stream = True)
        if res.status_code == 200:
            if target_file == None:
                # use downloaded file name from Content-Disposition
                # targetFile = res.headers['content-disposition']
                target_file = os.path.basename(path)

            f = open(target_file, 'w', 8192)
            for chunk in res.iter_content(8192):
                f.write(chunk)
            f.close()
            return True
        return False

    def getDirectoryAsZip(self, path, target_file):
        path = self.__normalizePath(path)
        res = requests.get(self.url + 'index.php/apps/files/ajax/download.php?dir=' + urllib.quote(path), auth = self.__auth, stream = True)
        if res.status_code == 200:
            if target_file == None:
                # use downloaded file name from Content-Disposition
                # targetFile = res.headers['content-disposition']
                target_file = os.path.basename(path)

            f = open(target_file, 'w', 8192)
            for chunk in res.iter_content(8192):
                f.write(chunk)
            f.close()
            return True
        return False

    def putFromString(self, target_path, data):
        return self.__makeDAVRequest('PUT', target_path, {'data': data})

    def putFromFile(self, target_path, local_source_file, **kwargs):
        if kwargs.get('chunked', True):
            return self.__putFromFileChunked(target_path, local_source_file, **kwargs)

        stat_result = os.stat(local_source_file)

        headers = {}
        if kwargs.get('keep_mtime', True):
            headers['X-OC-MTIME'] = stat_result.st_mtime

        if target_path[-1] == '/':
            target_path += os.path.basename(local_source_file)
        f = open(local_source_file, 'r', 8192)
        res = self.__makeDAVRequest('PUT', target_path, {'data': f, 'headers': headers})
        f.close()
        return res

    def putDirectory(self, target_path, local_directory, **kwargs):
        target_path = self.__normalizePath(target_path)
        if not target_path[-1] == '/':
            target_path += '/'
        gathered_files = []
        # gather files to upload
        for path, dirs, files in os.walk(local_directory):
            gathered_files.append((path, files))

        for path, files in gathered_files:
            self.mkdir(target_path + path + '/')
            for name in files:
                self.putFromFile(target_path + path + '/', path + '/' + name, **kwargs)

    def __putFromFileChunked(self, target_path, local_source_file, **kwargs):
        chunk_size = kwargs.get('chunk_size', 10 * 1024 * 1024)
        result = True
        transfer_id = int(time.time())

        target_path = self.__normalizePath(target_path)
        if target_path[-1] == '/':
            target_path += os.path.basename(local_source_file)
        # TODO: empty file should still work
        stat_result = os.stat(local_source_file)

        f = open(local_source_file, 'r', 8192)
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)

        headers = {}
        if kwargs.get('keep_mtime', True):
            headers['X-OC-MTIME'] = stat_result.st_mtime

        if size == 0:
            return self.__makeDAVRequest('PUT', target_path, {'data': '', 'headers': headers})

        chunk_count = size / chunk_size

        if chunk_count > 1:
            headers['OC-CHUNKED'] = 1

        if size % chunk_size > 0:
            chunk_count += 1
       
        for chunk_index in range(0, chunk_count):
            data = f.read(chunk_size)
            if chunk_count > 1:
                chunk_name = '%s-chunking-%s-%i-%i' % (target_path, transfer_id, chunk_count, chunk_index)
            else:
                chunk_name = target_path

            if not self.__makeDAVRequest('PUT', chunk_name, {'data': data, 'headers': headers}):
                result = False
                break

        f.close()
        return result

    def mkdir(self, path):
        if not path[-1] == '/':
            path = path + '/'
        return self.__makeDAVRequest('MKCOL', path)

    def delete(self, path):
        return self.__makeDAVRequest('DELETE', path)

    def shareFileWithLink(self, path):
        path = self.__normalizePath(path)
        post_data = {'shareType': 3, 'path': path}

        res = requests.post(self.__ocs_share_url + 'shares', auth = self.__auth, data = post_data)
        if res.status_code == 200:
            tree = ET.fromstring(res.text)
            data_el = tree.find('data')
            return PublicShare(
                int(data_el.find('id').text),
                path,
                data_el.find('url').text,
                data_el.find('token').text
            )
        return False

    @staticmethod
    def __normalizePath(path):
        if isinstance(path, File):
            path = path.path
        if len(path) == 0:
            return '/'
        if path[0] != '/':
            path = '/' + path
        return path

    def __makeDAVRequest(self, method, path, attributes = {}):
        if self.__DEBUG:
            print 'DAV request: %s %s' % (method, path)

        path = self.__normalizePath(path)
        attributes = attributes.copy()
        attributes['auth'] = self.__auth
        res = requests.request(method, self.__webdav_url + path, **attributes)
        if self.__DEBUG:
            print 'DAV status: %i' % res.status_code
        if res.status_code == 200 or res.status_code == 207:
            return self.__parseDAVResponse(res)
        if res.status_code == 204 or res.status_code == 201:
            return True
        return False

    def __parseDAVResponse(self, res):
        if res.status_code == 207:
            tree = ET.fromstring(res.text)
            items = []
            for child in tree:
                items.append(self.__parseDAVElement(child))
            return items
        return True

    def __parseDAVElement(self, el):
        href = urllib.unquote(self.__stripDAVPath(el.find('{DAV:}href').text))
        is_collection = el.find('{DAV:}collection')
        if is_collection:
            file_type = 'dir'
        else:
            file_type = 'file'

        file_attrs = {}
        attrs = el.find('{DAV:}propstat')
        attrs = attrs.find('{DAV:}prop')
        for attr in attrs:
            file_attrs[attr.tag] = attr.text

        return File(href, file_type, file_attrs)

    def __stripDAVPath(self, path):
        if (path.startswith(self.__davpath)):
            return path[len(self.__davpath):]
        return path

