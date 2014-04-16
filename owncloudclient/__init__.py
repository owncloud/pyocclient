#!/usr/bin/python
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
        self.url = url
        self.__auth = None

        url_components = urlparse.urlparse(url)
        self.__davpath = url_components.path + '/remote.php/webdav'
        self.__webdav_url = url + '/remote.php/webdav'

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

    def put(self, target_path, data):
        return self.__makeDAVRequest('PUT', target_path, {'data': data})

    def putFromFile(self, target_path, local_source_file):
        if target_path[-1] == '/':
            target_path += os.path.basename(local_source_file)
        f = open(local_source_file, 'r', 8192)
        res = self.__makeDAVRequest('PUT', target_path, {'data': f})
        f.close()
        return res

    def putFromFileChunked(self, target_path, local_source_file, chunk_size = 10 * 1024 * 1024):
        result = True
        transfer_id = int(time.time())

        target_path = self.__normalizePath(target_path)
        if target_path[-1] == '/':
            target_path += os.path.basename(local_source_file)
        # TODO: empty file should still work
        f = open(local_source_file, 'r', 8192)
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)

        chunk_count = size / chunk_size
        if size % chunk_size > 0:
            chunk_count += 1
       
        for chunk_index in range(0, chunk_count):
            data = f.read(chunk_size)
            chunk_name = '%s-chunking-%s-%i-%i' % (target_path, transfer_id, chunk_count, chunk_index)
            if not self.__makeDAVRequest('PUT', chunk_name, {'data': data, 'headers': {'OC-CHUNKED': 1}}):
                result = False
                break

        f.close()
        return result

    def mkdir(self, path):
        # FIXME: doesn't work
        return self.__makeDAVRequest('MKCOL', path)

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

