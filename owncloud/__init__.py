# -*- coding: utf-8 -*-
#
# vim: expandtab shiftwidth=4 softtabstop=4
#
"""ownCloud client module

Makes it possible to access files on a remote ownCloud instance,
share them or access application attributes.
"""

import datetime
import time
import urllib
import urlparse
import requests
import xml.etree.ElementTree as ET
import os

class ResponseError(Exception):
    def __init__(self, res):
        # TODO: how to retrieve the error message ?
        if type(res) is int:
            code = res
        else:
            code = res.status_code
        Exception.__init__(self, "HTTP error: %i" % code)
        self.status_code = code

class PublicShare():
    """Public share information"""
    def __init__(self, share_id, target_file, link, token):
        self.share_id = share_id
        self.target_file = target_file
        self.link = link
        self.token = token

    def __str__(self):
        return 'PublicShare(id=%i,path=%s,link=%s,token=%s)' % \
                (self.share_id, self.target_file, self.link, self.token)

class FileInfo():
    """File information"""

    __DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self, path, file_type = 'file', attributes = None):
        self.path = path
        if path[-1] == '/':
            path = path[0:-1]
        self.name = os.path.basename(path)
        self.file_type = file_type
        self.attributes = attributes or {}

    def get_name(self):
        """Returns the base name of the file (without path)
        
        :returns: name of the file
        """
        return self.name

    def get_size(self):
        """Returns the size of the file
        
        :returns: size of the file
        """
        if (self.attributes.has_key('{DAV:}getcontentlength')):
            return int(self.attributes['{DAV:}getcontentlength'])
        return None

    def get_etag(self):
        """Returns the file etag
        
        :returns: file etag
        """
        return self.attributes['{DAV:}getetag']

    def get_content_type(self):
        """Returns the file content type
        
        :returns: file content type
        """
        if self.attributes.has_key('{DAV:}getcontenttype'):
            return self.attributes['{DAV:}getcontenttype']

        if self.is_dir():
            return 'httpd/unix-directory'

        return None

    def get_last_modified(self):
        """Returns the last modified time
        
        :returns: last modified time
        :rtype: datetime object
        """
        return datetime.datetime.strptime(
                self.attributes['{DAV:}getlastmodified'],
                self.__DATE_FORMAT
                )

    def is_dir(self):
        """Returns whether the file info is a directory

        :returns: True if it is a directory, False otherwise
        """
        return self.file_type != 'file'

    def __str__(self):
        return 'File(path=%s,file_type=%s,attributes=%s)' % \
            (self.path, self.file_type, self.attributes)

    def __repr__(self):
        return self.__str__()

class Client():
    """ownCloud client"""

    OCS_SERVICE_SHARE = 'apps/files_sharing/api/v1'
    OCS_SERVICE_PRIVATEDATA = 'privatedata'

    def __init__(self, url, **kwargs):
        """Instantiates a client

        :param url: URL of the target ownCloud instance
        :param verify_certs: True (default) to verify SSL certificates, False otherwise
        :param debug: set to True to print debugging messages to stdout, defaults to False
        """
        if not url[-1] == '/':
            url = url + '/'

        self.url = url
        self.__session = None
        self.__debug = kwargs.get('debug', False)
        self.__verify_certs = kwargs.get('verify_certs', True)

        url_components = urlparse.urlparse(url)
        self.__davpath = url_components.path + 'remote.php/webdav'
        self.__webdav_url = url + 'remote.php/webdav'

    def login(self, user_id, password):
        """Authenticate to ownCloud.
        This will create a session on the server.

        :param user_id: user id
        :param password: password
        :raises: ResponseError in case an HTTP error status was returned
        """

        self.__session = requests.session()
        self.__session.verify = self.__verify_certs
        self.__session.auth = (user_id, password)
        # TODO: use another path to prevent that the server renders the file list page
        res = self.__session.get(self.url)
        if res.status_code == 200:
            # Remove auth, no need to re-auth every call
            # so sending the auth every time for now
            self.__session.auth = None
            return
        self.__session.close()
        self.__session = None
        raise ResponseError(res)

    def logout(self):
        """Log out the authenticated user and close the session.

        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        # TODO actual logout ?
        self.__session.close()
        return True

    def file_info(self, path):
        """Returns the file info for the given remote file
        
        :param path: path to the remote file 
        :returns: file info
        :rtype: :class:`FileInfo` object or `None` if file
            was not found
        :raises: ResponseError in case an HTTP error status was returned
        """
        res = self.__make_dav_request('PROPFIND', path)
        if res:
            return res[0]
        return None

    def list(self, path):
        """Returns the listing/contents of the given remote directory
        
        :param path: path to the remote directory 
        :returns: directory listing
        :rtype: array of :class:`FileInfo` objects
        :raises: ResponseError in case an HTTP error status was returned
        """
        if not path[-1] == '/':
            path += '/'
        res = self.__make_dav_request('PROPFIND', path)
        # first one is always the root, remove it from listing
        if res:
            return res[1:]
        return None

    def get_file_contents(self, path):
        """Returns the contents of a remote file

        :param path: path to the remote file
        :returns: file contents
        :rtype: binary data
        :raises: ResponseError in case an HTTP error status was returned
        """
        path = self.__normalize_path(path)
        res = self.__session.get(self.__webdav_url + path)
        if res.status_code == 200:
            return res.content
        return False

    def get_file(self, remote_path, local_file = None):
        """Downloads a remote file

        :param remote_path: path to the remote file
        :param local_file: optional path to the local file. If none specified,
            the file will be downloaded into the current directory
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        remote_path = self.__normalize_path(remote_path)
        res = self.__session.get(
                self.__webdav_url + remote_path,
                stream = True
                )
        if res.status_code == 200:
            if local_file == None:
                # use downloaded file name from Content-Disposition
                # local_file = res.headers['content-disposition']
                local_file = os.path.basename(remote_path)

            file_handle = open(local_file, 'w', 8192)
            for chunk in res.iter_content(8192):
                file_handle.write(chunk)
            file_handle.close()
            return True
        return False

    def get_directory_as_zip(self, remote_path, local_file):
        """Downloads a remote directory as zip

        :param remote_path: path to the remote directory to download
        :param local_file: path and name of the target local file
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        remote_path = self.__normalize_path(remote_path)
        url = self.url + 'index.php/apps/files/ajax/download.php?dir=' \
            + urllib.quote(remote_path)
        res = self.__session.get(
                url,
                stream = True
                )
        if res.status_code == 200:
            if local_file == None:
                # use downloaded file name from Content-Disposition
                # targetFile = res.headers['content-disposition']
                local_file = os.path.basename(remote_path)

            file_handle = open(local_file, 'w', 8192)
            for chunk in res.iter_content(8192):
                file_handle.write(chunk)
            file_handle.close()
            return True
        return False

    def put_file_contents(self, remote_path, data):
        """Write data into a remote file

        :param remote_path: path of the remote file
        :param data: data to write into the remote file
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        return self.__make_dav_request('PUT', remote_path, data = data)

    def put_file(self, remote_path, local_source_file, **kwargs):
        """Upload a file

        :param remote_path: path to the target file. A target directory can
            also be specified instead by appending a "/"
        :param local_source_file: path to the local file to upload
        :param chunked: (optional) use file chunking (defaults to True)
        :param chunk_size: (optional) chunk size in bytes, defaults to 10 MB
        :param keep_mtime: (optional) also update the remote file to the same
            mtime as the local one, defaults to True
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        if kwargs.get('chunked', True):
            return self.__put_file_chunked(
                    remote_path,
                    local_source_file,
                    **kwargs
                    )

        stat_result = os.stat(local_source_file)

        headers = {}
        if kwargs.get('keep_mtime', True):
            headers['X-OC-MTIME'] = stat_result.st_mtime

        if remote_path[-1] == '/':
            remote_path += os.path.basename(local_source_file)
        file_handle = open(local_source_file, 'r', 8192)
        res = self.__make_dav_request(
                'PUT',
                remote_path,
                data = file_handle,
                headers = headers
                )
        file_handle.close()
        return res

    def put_directory(self, target_path, local_directory, **kwargs):
        """Upload a directory with all its contents

        :param target_path: path of the directory to upload into
        :param local_directory: path to the local directory to upload
        :param \*\*kwargs: optional arguments that ``put_file`` accepts
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        target_path = self.__normalize_path(target_path)
        if not target_path[-1] == '/':
            target_path += '/'
        gathered_files = []

        if not local_directory[-1] == '/':
            local_directory += '/'

        basedir = os.path.basename(local_directory[0: -1]) + '/'
        # gather files to upload
        for path, _, files in os.walk(local_directory):
            gathered_files.append(
                    (path, basedir + path[len(local_directory):], files)
                    )

        for path, remote_path, files in gathered_files:
            self.mkdir(target_path + remote_path + '/')
            for name in files:
                if not self.put_file(
                        target_path + remote_path + '/',
                        path + '/' + name,
                        **kwargs
                        ):
                    return False
        return True

    def __put_file_chunked(self, remote_path, local_source_file, **kwargs):
        """Uploads a file using chunks. If the file is smaller than
        ``chunk_size`` it will be uploaded directly.

        :param remote_path: path to the target file. A target directory can
        also be specified instead by appending a "/"
        :param local_source_file: path to the local file to upload
        :param \*\*kwargs: optional arguments that ``put_file`` accepts
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        chunk_size = kwargs.get('chunk_size', 10 * 1024 * 1024)
        result = True
        transfer_id = int(time.time())

        remote_path = self.__normalize_path(remote_path)
        if remote_path[-1] == '/':
            remote_path += os.path.basename(local_source_file)

        stat_result = os.stat(local_source_file)

        file_handle = open(local_source_file, 'r', 8192)
        file_handle.seek(0, os.SEEK_END)
        size = file_handle.tell()
        file_handle.seek(0)

        headers = {}
        if kwargs.get('keep_mtime', True):
            headers['X-OC-MTIME'] = stat_result.st_mtime

        if size == 0:
            return self.__make_dav_request(
                    'PUT',
                    remote_path,
                    data = '',
                    headers = headers
                    )

        chunk_count = size / chunk_size

        if chunk_count > 1:
            headers['OC-CHUNKED'] = 1

        if size % chunk_size > 0:
            chunk_count += 1
       
        for chunk_index in range(0, chunk_count):
            data = file_handle.read(chunk_size)
            if chunk_count > 1:
                chunk_name = '%s-chunking-%s-%i-%i' % \
                        (remote_path, transfer_id, chunk_count, chunk_index)
            else:
                chunk_name = remote_path

            if not self.__make_dav_request(
                    'PUT',
                    chunk_name,
                    data = data,
                    headers = headers
                ):
                result = False
                break

        file_handle.close()
        return result

    def mkdir(self, path):
        """Creates a remote directory

        :param path: path to the remote directory to create
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        if not path[-1] == '/':
            path = path + '/'
        return self.__make_dav_request('MKCOL', path)

    def delete(self, path):
        """Deletes a remote file or directory

        :param path: path to the file or directory to delete
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        return self.__make_dav_request('DELETE', path)

    def share_file_with_link(self, path):
        """Shares a remote file with link

        :param path: path to the remote file to share
        :returns: instance of :class:`PublicShare` with the share info
            or False if the operation failed
        :raises: ResponseError in case an HTTP error status was returned
        """
        path = self.__normalize_path(path)
        post_data = {'shareType': 3, 'path': path}

        res = self.__make_ocs_request(
                'POST',
                self.OCS_SERVICE_SHARE,
                'shares',
                data = post_data
                )
        if res.status_code == 200:
            tree = ET.fromstring(res.text)
            self.__check_ocs_status(tree)
            data_el = tree.find('data')
            return PublicShare(
                int(data_el.find('id').text),
                path,
                data_el.find('url').text,
                data_el.find('token').text
            )
        raise ResponseError(res)

    def get_attribute(self, app = None, key = None):
        """Returns an application attribute

        :param app: application id
        :param key: attribute key or None to retrieve all values for the
            given application
        :returns: attribute value if key was specified, or an array of tuples
            (key, value) for each attribute
        :raises: ResponseError in case an HTTP error status was returned
        """
        path = 'getattribute'
        if app != None:
            path += '/' + urllib.quote(app)
            if key != None:
                path += '/' + urllib.quote(key)
        res = self.__make_ocs_request(
                'GET',
                self.OCS_SERVICE_PRIVATEDATA,
                path
                )
        if res.status_code == 200:
            tree = ET.fromstring(res.text)
            self.__check_ocs_status(tree)
            values = []
            for element in tree.find('data').iter('element'):
                app_text = element.find('app').text
                key_text = element.find('key').text
                value_text = element.find('value').text or ''
                if key == None:
                    if app == None:
                        values.append((app_text, key_text, value_text))
                    else:
                        values.append((key_text, value_text))
                else:
                    return value_text

            if len(values) == 0 and key != None:
                return None
            return values
        raise ResponseError(res)

    def set_attribute(self, app, key, value):
        """Sets an application attribute

        :param app: application id
        :param key: key of the attribute to set
        :param value: value to set
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        path = 'setattribute/' + urllib.quote(app) + '/' + urllib.quote(key)
        res = self.__make_ocs_request(
                'POST',
                self.OCS_SERVICE_PRIVATEDATA,
                path,
                data = {'value': value}
                )
        if res.status_code == 200:
            tree = ET.fromstring(res.text)
            self.__check_ocs_status(tree)
            return True
        raise ResponseError(res)

    def delete_attribute(self, app, key):
        """Deletes an application attribute

        :param app: application id
        :param key: key of the attribute to delete
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        path = 'deleteattribute/' + urllib.quote(app) + '/' + urllib.quote(key)
        res = self.__make_ocs_request(
                'POST',
                self.OCS_SERVICE_PRIVATEDATA,
                path
                )
        if res.status_code == 200:
            tree = ET.fromstring(res.text)
            self.__check_ocs_status(tree)
            return True
        raise ResponseError(res)

    @staticmethod
    def __normalize_path(path):
        """Makes sure the path starts with a "/"
        """
        if isinstance(path, FileInfo):
            path = path.path
        if len(path) == 0:
            return '/'
        if path[0] != '/':
            path = '/' + path
        return path

    @staticmethod
    def __check_ocs_status(tree):
        """Checks the status code of an OCS request

        :param tree: response parsed with elementtree
        :raises: ResponseError if the status is not 200
        """
        code_el = tree.find('meta/statuscode')
        if code_el is not None and code_el.text != '100':
            raise ResponseError(int(code_el.text))

    def __make_ocs_request(self, method, service, action, **kwargs):
        """Makes a OCS API request

        :param method: HTTP method
        :param service: service name
        :param action: action path
        :param \*\*kwargs: optional arguments that ``requests.Request.request`` accepts
        :returns :class:`requests.Response` instance
        """
        path = 'ocs/v1.php/' + service + '/' + action
        if self.__debug:
            print 'OCS request: %s %s' % (method, self.url + path)

        attributes = kwargs.copy()

        if not attributes.has_key('headers'):
            attributes['headers'] = {}

        attributes['headers']['OCS-APIREQUEST'] = 'true'

        res = self.__session.request(method, self.url + path, **attributes)
        return res

    def __make_dav_request(self, method, path, **kwargs):
        """Makes a WebDAV request

        :param method: HTTP method
        :param path: remote path of the targetted file
        :param \*\*kwargs: optional arguments that ``requests.Request.request`` accepts
        :returns array of :class:`FileInfo` if the response
        contains it, or True if the operation succeded, False
        if it didn't
        """
        if self.__debug:
            print 'DAV request: %s %s' % (method, path)

        path = self.__normalize_path(path)
        res = self.__session.request(method, self.__webdav_url + path, **kwargs)
        if self.__debug:
            print 'DAV status: %i' % res.status_code
        if res.status_code == 200 or res.status_code == 207:
            return self.__parse_dav_response(res)
        if res.status_code == 204 or res.status_code == 201:
            return True
        raise ResponseError(res)

    def __parse_dav_response(self, res):
        """Parses the DAV responses from a multi-status response

        :param res: DAV response
        :returns array of :class:`FileInfo` or False if
        the operation did not succeed
        """
        if res.status_code == 207:
            tree = ET.fromstring(res.text)
            items = []
            for child in tree:
                items.append(self.__parse_dav_element(child))
            return items
        return True

    def __parse_dav_element(self, dav_response):
        """Parses a single DAV element

        :param el: ElementTree element containing a single DAV response
        :returns :class:`FileInfo`
        """
        href = urllib.unquote(
                self.__strip_dav_path(dav_response.find('{DAV:}href').text)
                )
        file_type = 'file'
        if href[-1] == '/':
            file_type = 'dir'

        file_attrs = {}
        attrs = dav_response.find('{DAV:}propstat')
        attrs = attrs.find('{DAV:}prop')
        for attr in attrs:
            file_attrs[attr.tag] = attr.text

        return FileInfo(href, file_type, file_attrs)

    def __strip_dav_path(self, path):
        """Removes the leading "remote.php/webdav" path from the given path

        :param path: path containing the remote DAV path "remote.php/webdav"
        :returns: path stripped of the remote DAV path
        """
        if (path.startswith(self.__davpath)):
            return path[len(self.__davpath):]
        return path

