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
import requests
import xml.etree.ElementTree as ET
import os
import math
import six
import logging
from six.moves.urllib import parse


LOGGER = logging.getLogger(__name__)


class ResponseError(Exception):
    def __init__(self, res, errorType):
        if type(res) is int:
            code = res
        else:
            code = res.status_code
            self.res = res
        Exception.__init__(self, errorType + " error: %i" % code)
        self.status_code = code

    def get_resource_body(self):
        if self.res is not None:
            return self.res.content
        else:
            return None


class OCSResponseError(ResponseError):
    def __init__(self, res):
        ResponseError.__init__(self, res, "OCS")

    def get_resource_body(self):
        if self.res is not None:
            import xml.etree.ElementTree as ElementTree
            try:
                root_element = ElementTree.fromstringlist(self.res.content)
                if root_element.tag == 'message':
                    return root_element.text
            except ET.ParseError:
                return self.res.content
        else:
            return None


class HTTPResponseError(ResponseError):
    def __init__(self, res):
        ResponseError.__init__(self, res, "HTTP")


class ShareInfo(object):
    """Share information"""

    def __init__(self, share_info):
        self.share_info = {}
        # remove unneeded attributes
        del_attrs = ['item_type', 'item_source', 'file_source', 'parent',
                     'storage', 'mail_send']
        for k, v in share_info.items():
            if k not in del_attrs:
                self.share_info[k] = v
        self.share_id = self._get_int('id')
        if 'token' in self.share_info:
            self.token = self.share_info['token']

    def get_id(self):
        """Returns the id of the share

        :returns: id of the share
        """
        return self._get_int('id')

    def get_share_type(self):
        """Returns the type of the share.
        See OCS_SHARE_TYPE_* constants.

        :returns: share type
        """
        return self._get_int('share_type')

    def get_share_with(self):
        """Returns the share recipient.
        If share type is OCS_SHARE_TYPE_USER, then the recipient is the name of
        the user.
        For OCS_SHARE_TYPE_GROUP it is the name of the group.
        Otherwise this value is None.

        :returns: name of the share recipient
        """
        if 'share_with' in self.share_info:
            return self.share_info['share_with']
        return None

    def get_share_with_displayname(self):
        """Returns the share recipient displayname.
        If share_with_displayname cannot be returned, None is returned instead
        :returns: name of the share recipient
        """
        if 'share_with_displayname' in self.share_info:
            return self.share_info['share_with_displayname']
        return None

    def get_path(self):
        """Returns the path of the shared file/folder relative to the
        caller's filesystem.

        :returns: path to the shared file/folder
        """
        if 'path' in self.share_info:
            return self.share_info['path']
        return None

    def get_permissions(self):
        """Returns the share permissions.
        See OCS_PERMISSION_* constants.

        :returns: share permissions
        """
        return self._get_int('permissions')

    def get_share_time(self):
        """Returns the share time.

        :returns: share timestamp
        :rtype: datetime object
        """
        return datetime.datetime.fromtimestamp(
            self._get_int('stime')
        )

    def get_expiration(self):
        """Returns the expiration date.

        :returns: expiration date
        :rtype: datetime object
        """
        exp = self._get_int('expiration')
        if exp is not None:
            return datetime.datetime.fromtimestamp(
                exp
            )
        return None

    def get_token(self):
        if 'token' in self.share_info:
            return self.share_info['token']
        return None

    def get_link(self):
        if 'url' in self.share_info:
            return self.share_info['url']
        return None

    def get_uid_owner(self):
        """Returns the user id of the owner.

        :returns: owner user id
        """
        if 'uid_owner' in self.share_info:
            return self.share_info['uid_owner']
        return None

    def get_displayname_owner(self):
        """Returns the display name of the owner.

        :returns: display name of owner
        """
        if 'displayname_owner' in self.share_info:
            return self.share_info['displayname_owner']
        return None

    def get_name(self):
        """Returns the name of a link share

        :returns: name of link share
        """
        if 'name' in self.share_info:
            return self.share_info['name']
        return None

    def __str__(self):
        info = ''
        for k, v in self.share_info.items():
            info += '%s=%s,' % (k, v)
        return 'ShareInfo(%s)' % info[:-1]

    def __repr__(self):
        return self.__str__()

    def _get_int(self, key):
        """Simple wrapper which converts value to Integer
           in silently manner (w/o raising exception)"""
        try:
            value = int(self.share_info[key])
            return value
        except:
            return None


class PublicShare(ShareInfo):
    """Public share information"""

    def __init__(self, share_id, target_file, link, token):
        self.share_id = share_id
        self.target_file = target_file
        self.link = link
        self.token = token

    def __str__(self):
        return 'PublicShare(id=%i,path=%s,link=%s,token=%s)' % \
               (self.share_id, self.target_file, self.link, self.token)


class FileInfo(object):
    """File information"""

    _DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self, path, file_type='file', attributes=None):
        self.path = path
        if path.endswith('/'):
            path = path[0:-1]
        self.name = os.path.basename(path)
        self.file_type = file_type
        self.attributes = attributes or {}

    def get_name(self):
        """Returns the base name of the file without path

        :returns: name of the file
        """
        return self.name

    def get_path(self):
        """Returns the full path to the file without name and without
        trailing slash

        :returns: path to the file
        """
        return os.path.dirname(self.path)

    def get_size(self):
        """Returns the size of the file

        :returns: size of the file
        """
        if '{DAV:}getcontentlength' in self.attributes:
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
        if '{DAV:}getcontenttype' in self.attributes:
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
            self._DATE_FORMAT
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


class Client(object):
    """ownCloud client"""

    OCS_BASEPATH = 'ocs/v1.php/'
    OCS_SERVICE_SHARE = 'apps/files_sharing/api/v1'
    OCS_SERVICE_PRIVATEDATA = 'privatedata'
    OCS_SERVICE_CLOUD = 'cloud'

    # constants from lib/public/constants.php
    OCS_PERMISSION_READ = 1
    OCS_PERMISSION_UPDATE = 2
    OCS_PERMISSION_CREATE = 4
    OCS_PERMISSION_DELETE = 8
    OCS_PERMISSION_SHARE = 16
    OCS_PERMISSION_ALL = 31
    # constants from lib/public/share.php
    OCS_SHARE_TYPE_USER = 0
    OCS_SHARE_TYPE_GROUP = 1
    OCS_SHARE_TYPE_LINK = 3
    OCS_SHARE_TYPE_REMOTE = 6

    def __init__(self, url, **kwargs):
        """Instantiates a client

        :param url: URL of the target ownCloud instance
        :param verify_certs: True (default) to verify SSL certificates, False otherwise
        :param dav_endpoint_version: None (default) to force using a specific endpoint version
        instead of relying on capabilities
        :param debug: set to True to log debugging messages with python logging, defaults to False
        """
        if not url.endswith('/'):
            url += '/'

        self.url = url
        self._session = None
        self._debug = kwargs.get('debug', False)
        self._verify_certs = kwargs.get('verify_certs', True)
        self._dav_endpoint_version = kwargs.get('dav_endpoint_version', True)

        self._capabilities = None
        self._version = None

    def login(self, user_id, password):
        """Authenticate to ownCloud.
        This will create a session on the server.

        :param user_id: user id
        :param password: password
        :raises: HTTPResponseError in case an HTTP error status was returned
        """

        self._session = requests.session()
        self._session.verify = self._verify_certs
        self._session.auth = (user_id, password)

        try:
            self._update_capabilities()

            url_components = parse.urlparse(self.url)
            if self._dav_endpoint_version == 1:
                self._davpath = url_components.path + 'remote.php/dav/files/' + parse.quote(user_id)
                self._webdav_url = self.url + 'remote.php/dav/files/' + parse.quote(user_id)
            else:
                self._davpath = url_components.path + 'remote.php/webdav'
                self._webdav_url = self.url + 'remote.php/webdav'

        except HTTPResponseError as e:
            self._session.close()
            self._session = None
            raise e

    def logout(self):
        """Log out the authenticated user and close the session.

        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        # TODO actual logout ?
        self._session.close()
        return True

    def anon_login(self, folder_token, folder_password=''):
        self._session = requests.session()
        self._session.verify = self._verify_certs
        self._session.auth = (folder_token, folder_password)

        url_components = parse.urlparse(self.url)
        self._davpath = url_components.path + 'public.php/webdav'
        self._webdav_url = self.url + 'public.php/webdav'
    
    @classmethod
    def from_public_link(cls, public_link, folder_password='', **kwargs):
        public_link_components = parse.urlparse(public_link)
        url = public_link_components.scheme + '://' + public_link_components.hostname
        if public_link_components.port:
            url += ":" + public_link_components.port
        folder_token = public_link_components.path.split('/')[-1]
        anon_session = cls(url, **kwargs)
        anon_session.anon_login(folder_token, folder_password=folder_password)
        return anon_session

    def drop_file(self, file_name):
        """ Convenience wrapper for put_file """
        destination = '/' + os.path.basename(file_name)
        return self.put_file(destination, file_name)

    def file_info(self, path, properties=None):
        """Returns the file info for the given remote file

        :param path: path to the remote file
        :param properties: a list of properties to request (optional)
        :returns: file info
        :rtype: :class:`FileInfo` object or `None` if file
            was not found
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if properties:
            root = ET.Element('d:propfind',
                              {
                                  'xmlns:d': "DAV:",
                                  'xmlns:nc': "http://nextcloud.org/ns",
                                  'xmlns:oc': "http://owncloud.org/ns"
                              })
            prop = ET.SubElement(root, 'd:prop')
            for p in properties:
                ET.SubElement(prop, p)
            data = ET.tostring(root)
        else:
            data = None
        res = self._make_dav_request('PROPFIND', path, headers={'Depth': '0'}, data=data)
        if res:
            return res[0]
        return None

    def list(self, path, depth=1, properties=None):
        """Returns the listing/contents of the given remote directory

        :param path: path to the remote directory
        :param depth: depth of the listing, integer or "infinity"
        :param properties: a list of properties to request (optional)
        :returns: directory listing
        :rtype: array of :class:`FileInfo` objects
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if not path.endswith('/'):
            path += '/'

        headers = {}
        if isinstance(depth, int) or depth == "infinity":
            headers['Depth'] = str(depth)

        if properties:
            root = ET.Element('d:propfind',
                              {
                                  'xmlns:d': "DAV:",
                                  'xmlns:nc': "http://nextcloud.org/ns",
                                  'xmlns:oc': "http://owncloud.org/ns"
                              })
            prop = ET.SubElement(root, 'd:prop')
            for p in properties:
                ET.SubElement(prop, p)
            data = ET.tostring(root)
        else:
            data = None

        res = self._make_dav_request('PROPFIND', path, headers=headers, data=data)
        # first one is always the root, remove it from listing
        if res:
            return res[1:]
        return None

    def get_file_contents(self, path):
        """Returns the contents of a remote file

        :param path: path to the remote file
        :returns: file contents
        :rtype: binary data
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        path = self._normalize_path(path)
        res = self._session.get(
            self._webdav_url + parse.quote(self._encode_string(path))
        )
        if res.status_code == 200:
            return res.content
        elif res.status_code >= 400:
            raise HTTPResponseError(res)
        return False

    def get_file(self, remote_path, local_file=None):
        """Downloads a remote file

        :param remote_path: path to the remote file
        :param local_file: optional path to the local file. If none specified,
            the file will be downloaded into the current directory
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        remote_path = self._normalize_path(remote_path)
        res = self._session.get(
            self._webdav_url + parse.quote(self._encode_string(remote_path)),
            stream=True
        )
        if res.status_code == 200:
            if local_file is None:
                # use downloaded file name from Content-Disposition
                # local_file = res.headers['content-disposition']
                local_file = os.path.basename(remote_path)

            file_handle = open(local_file, 'wb', 8192)
            for chunk in res.iter_content(8192):
                file_handle.write(chunk)
            file_handle.close()
            return True
        elif res.status_code >= 400:
            raise HTTPResponseError(res)
        return False

    def get_directory_as_zip(self, remote_path, local_file):
        """Downloads a remote directory as zip

        :param remote_path: path to the remote directory to download
        :param local_file: path and name of the target local file
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        remote_path = self._normalize_path(remote_path)
        url = self.url + 'index.php/apps/files/ajax/download.php?dir=' \
              + parse.quote(remote_path)
        res = self._session.get(url, stream=True)
        if res.status_code == 200:
            if local_file is None:
                # use downloaded file name from Content-Disposition
                # targetFile = res.headers['content-disposition']
                local_file = os.path.basename(remote_path)

            file_handle = open(local_file, 'wb', 8192)
            for chunk in res.iter_content(8192):
                file_handle.write(chunk)
            file_handle.close()
            return True
        elif res.status_code >= 400:
            raise HTTPResponseError(res)
        return False

    def put_file_contents(self, remote_path, data):
        """Write data into a remote file

        :param remote_path: path of the remote file
        :param data: data to write into the remote file
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        return self._make_dav_request('PUT', remote_path, data=data)

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
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if kwargs.get('chunked', True):
            return self._put_file_chunked(
                remote_path,
                local_source_file,
                **kwargs
            )

        stat_result = os.stat(local_source_file)

        headers = {}
        if kwargs.get('keep_mtime', True):
            headers['X-OC-MTIME'] = str(int(stat_result.st_mtime))

        if remote_path[-1] == '/':
            remote_path += os.path.basename(local_source_file)
        file_handle = open(local_source_file, 'rb', 8192)
        res = self._make_dav_request(
            'PUT',
            remote_path,
            data=file_handle,
            headers=headers
        )
        file_handle.close()
        return res

    def put_directory(self, target_path, local_directory, **kwargs):
        """Upload a directory with all its contents

        :param target_path: path of the directory to upload into
        :param local_directory: path to the local directory to upload
        :param \*\*kwargs: optional arguments that ``put_file`` accepts
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        target_path = self._normalize_path(target_path)
        if not target_path.endswith('/'):
            target_path += '/'
        gathered_files = []

        if not local_directory.endswith('/'):
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
                if not self.put_file(target_path + remote_path + '/',
                                     path + '/' + name, **kwargs):
                    return False
        return True

    def _put_file_chunked(self, remote_path, local_source_file, **kwargs):
        """Uploads a file using chunks. If the file is smaller than
        ``chunk_size`` it will be uploaded directly.

        :param remote_path: path to the target file. A target directory can
        also be specified instead by appending a "/"
        :param local_source_file: path to the local file to upload
        :param \*\*kwargs: optional arguments that ``put_file`` accepts
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        chunk_size = kwargs.get('chunk_size', 10 * 1024 * 1024)
        result = True
        transfer_id = int(time.time())

        remote_path = self._normalize_path(remote_path)
        if remote_path.endswith('/'):
            remote_path += os.path.basename(local_source_file)

        stat_result = os.stat(local_source_file)

        file_handle = open(local_source_file, 'rb', 8192)
        file_handle.seek(0, os.SEEK_END)
        size = file_handle.tell()
        file_handle.seek(0)

        headers = {}
        if kwargs.get('keep_mtime', True):
            headers['X-OC-MTIME'] = str(int(stat_result.st_mtime))

        if size == 0:
            return self._make_dav_request(
                'PUT',
                remote_path,
                data='',
                headers=headers
            )

        chunk_count = int(math.ceil(float(size) / float(chunk_size)))

        if chunk_count > 1:
            headers['OC-CHUNKED'] = '1'

        for chunk_index in range(0, int(chunk_count)):
            data = file_handle.read(chunk_size)
            if chunk_count > 1:
                chunk_name = '%s-chunking-%s-%i-%i' % \
                             (remote_path, transfer_id, chunk_count,
                              chunk_index)
            else:
                chunk_name = remote_path

            if not self._make_dav_request(
                    'PUT',
                    chunk_name,
                    data=data,
                    headers=headers
            ):
                result = False
                break

        file_handle.close()
        return result

    def mkdir(self, path):
        """Creates a remote directory

        :param path: path to the remote directory to create
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if not path.endswith('/'):
            path += '/'
        return self._make_dav_request('MKCOL', path)

    def delete(self, path):
        """Deletes a remote file or directory

        :param path: path to the file or directory to delete
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        return self._make_dav_request('DELETE', path)

    def list_open_remote_share(self):
        """List all pending remote shares

        :returns: array of pending remote shares
        :raises: HTTPResponseError in case an HTTP error status was returned
        """

        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_SHARE,
            'remote_shares/pending'
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            shares = []
            for element in tree.find('data').iter('element'):
                share_attr = {}
                for child in element:
                    key = child.tag
                    value = child.text
                    share_attr[key] = value
                shares.append(share_attr)
            return shares
        raise HTTPResponseError(res)

    def accept_remote_share(self, share_id):
        """Accepts a remote share

        :param share_id: Share ID (int)
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if not isinstance(share_id, int):
            return False

        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_SHARE,
            'remote_shares/pending/' + str(share_id)
        )
        if res.status_code == 200:
            return res
        raise HTTPResponseError(res)

    def decline_remote_share(self, share_id):
        """Declines a remote share

        :param share_id: Share ID (int)
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if not isinstance(share_id, int):
            return False

        res = self._make_ocs_request(
            'DELETE',
            self.OCS_SERVICE_SHARE,
            'remote_shares/pending/' + str(share_id)
        )
        if res.status_code == 200:
            return res
        raise HTTPResponseError(res)

    def delete_share(self, share_id):
        """Unshares a file or directory

        :param share_id: Share ID (int)
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if not isinstance(share_id, int):
            return False

        res = self._make_ocs_request(
            'DELETE',
            self.OCS_SERVICE_SHARE,
            'shares/' + str(share_id)
        )
        if res.status_code == 200:
            return res
        raise HTTPResponseError(res)

    def update_share(self, share_id, **kwargs):
        """Updates a given share

        :param share_id: (int) Share ID
        :param perms: (int) update permissions (see share_file_with_user() below)
        :param password: (string) updated password for public link Share
        :param public_upload: (boolean) enable/disable public upload for public shares
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """

        perms = kwargs.get('perms', None)
        password = kwargs.get('password', None)
        public_upload = kwargs.get('public_upload', None)
        if (isinstance(perms, int)) and (perms > self.OCS_PERMISSION_ALL):
            perms = None
        if not (perms or password or (public_upload is not None)):
            return False
        if not isinstance(share_id, int):
            return False

        data = {}
        if perms:
            data['permissions'] = perms
        if isinstance(password, six.string_types):
            data['password'] = password
        if (public_upload is not None) and (isinstance(public_upload, bool)):
            data['publicUpload'] = str(public_upload).lower()

        res = self._make_ocs_request(
            'PUT',
            self.OCS_SERVICE_SHARE,
            'shares/' + str(share_id),
            data=data
        )
        if res.status_code == 200:
            return True
        raise HTTPResponseError(res)

    def move(self, remote_path_source, remote_path_target):
        """Moves a remote file or directory

        :param remote_path_source: source file or folder to move
        :param remote_path_target: target file to which to move
        the source file. A target directory can also be specified
        instead by appending a "/"
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """

        return self._webdav_move_copy(remote_path_source, remote_path_target,
                                       "MOVE")

    def copy(self, remote_path_source, remote_path_target):
        """Copies a remote file or directory

        :param remote_path_source: source file or folder to copy
        :param remote_path_target: target file to which to copy

        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        return self._webdav_move_copy(remote_path_source, remote_path_target,
                                       "COPY")

    def share_file_with_link(self, path, **kwargs):
        """Shares a remote file with link

        :param path: path to the remote file to share
        :param perms (optional): permission of the shared object
        defaults to read only (1)
        :param public_upload (optional): allows users to upload files or folders
        :param password (optional): sets a password
        http://doc.owncloud.org/server/6.0/admin_manual/sharing_api/index.html
        :param name (optional): display name for the link
        :returns: instance of :class:`ShareInfo` with the share info
            or False if the operation failed
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        perms = kwargs.get('perms', None)
        public_upload = kwargs.get('public_upload', 'false')
        password = kwargs.get('password', None)
        name = kwargs.get('name', None)

        path = self._normalize_path(path)
        post_data = {
            'shareType': self.OCS_SHARE_TYPE_LINK,
            'path': self._encode_string(path),
        }
        if (public_upload is not None) and (isinstance(public_upload, bool)):
            post_data['publicUpload'] = str(public_upload).lower()
        if isinstance(password, six.string_types):
            post_data['password'] = password
        if name is not None:
            post_data['name'] = self._encode_string(name)
        if perms:
            post_data['permissions'] = perms

        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_SHARE,
            'shares',
            data=post_data
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            data_el = tree.find('data')
            return ShareInfo(
                                {
                                    'id': data_el.find('id').text,
                                    'path': path,
                                    'url': data_el.find('url').text,
                                    'token': data_el.find('token').text,
                                    'name': data_el.find('name').text
                                }
            )
        raise HTTPResponseError(res)

    def is_shared(self, path):
        """Checks whether a path is already shared

        :param path: path to the share to be checked
        :returns: True if the path is already shared, else False
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        # make sure that the path exist - if not, raise HTTPResponseError
        self.file_info(path)
        try:
            result = self.get_shares(path)
            if result:
                return len(result) > 0
        except OCSResponseError as e:
            if e.status_code != 404:
                raise e
            return False
        return False

    def get_share(self, share_id):
        """Returns share information about known share

        :param share_id: id of the share to be checked
        :returns: instance of ShareInfo class
        :raises: ResponseError in case an HTTP error status was returned
        """
        if (share_id is None) or not (isinstance(share_id, int)):
            return None

        res = self._make_ocs_request(
                'GET',
                self.OCS_SERVICE_SHARE,
                'shares/' + str(share_id)
                )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            return self._get_shareinfo(tree.find('data').find('element'))
        raise HTTPResponseError(res)

    def get_shares(self, path='', **kwargs):
        """Returns array of shares

        :param path: path to the share to be checked
        :param reshares: (optional, boolean) returns not only the shares from
            the current user but all shares from the given file (default: False)
        :param subfiles: (optional, boolean) returns all shares within
            a folder, given that path defines a folder (default: False)
        :param shared_with_me: (optional, boolean) returns all shares which are
            shared with me (default: False)
        :returns: array of shares ShareInfo instances or empty array if the operation failed
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        if not (isinstance(path, six.string_types)):
            return None

        data = 'shares'
        if path != '':
            data += '?'
            path = self._encode_string(self._normalize_path(path))
            args = {'path': path}
            reshares = kwargs.get('reshares', False)
            if isinstance(reshares, bool) and reshares:
                args['reshares'] = reshares
            subfiles = kwargs.get('subfiles', False)
            if isinstance(subfiles, bool) and subfiles:
                args['subfiles'] = str(subfiles).lower()

            shared_with_me = kwargs.get('shared_with_me', False)
            if isinstance(shared_with_me, bool) and shared_with_me:
                args['shared_with_me'] = "true"
                del args['path']

            data += parse.urlencode(args)

        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_SHARE,
            data
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            shares = []
            for element in tree.find('data').iter('element'):
                '''share_attr = {}
                for child in element:
                    key = child.tag
                    value = child.text
                    share_attr[key] = value
                shares.append(share_attr)'''
                shares.append(self._get_shareinfo(element))
            return shares
        raise HTTPResponseError(res)

    def create_user(self, user_name, initial_password):
        """Create a new user with an initial password via provisioning API.
        It is not an error, if the user already existed before.
        If you get back an error 999, then the provisioning API is not enabled.

        :param user_name:  name of user to be created
        :param initial_password:  password for user being created
        :returns: True on success
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_CLOUD,
            'users',
            data={'password': initial_password, 'userid': user_name}
        )

        # We get 200 when the user was just created.
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])
            return True

        raise HTTPResponseError(res)

    def delete_user(self, user_name):
        """Deletes a user via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :param user_name:  name of user to be deleted
        :returns: True on success
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'DELETE',
            self.OCS_SERVICE_CLOUD,
            'users/' + user_name
        )

        # We get 200 when the user was deleted.
        if res.status_code == 200:
            return True

        raise HTTPResponseError(res)

    def user_exists(self, user_name):
        """Checks a user via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :param user_name:  name of user to be checked
        :returns: True if user found

        """
        users = self.search_users(user_name)

        return user_name in users

    def search_users(self, user_name):
        """Searches for users via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :param user_name:  name of user to be searched for
        :returns: list of usernames that contain user_name as substring
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        action_path = 'users'
        if user_name:
            action_path += '?search={}'.format(user_name)

        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_CLOUD,
            action_path
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            users = [x.text for x in tree.findall('data/users/element')]

            return users

        raise HTTPResponseError(res)

    def get_users(self):
        """Get users via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :returns: list of usernames
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        return self.search_users('')

    def set_user_attribute(self, user_name, key, value):
        """Sets a user attribute

        :param user_name: name of user to modify
        :param key: key of the attribute to set
        :param value: value to set
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """

        res = self._make_ocs_request(
            'PUT',
            self.OCS_SERVICE_CLOUD,
            'users/' + parse.quote(user_name),
            data={'key': self._encode_string(key),
                  'value': self._encode_string(value)}
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])
            return True
        raise HTTPResponseError(res)

    def add_user_to_group(self, user_name, group_name):
        """Adds a user to a group.

        :param user_name:  name of user to be added
        :param group_name:  name of group user is to be added to
        :returns: True if user added
        :raises: HTTPResponseError in case an HTTP error status was returned

        """

        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_CLOUD,
            'users/' + user_name + '/groups',
            data={'groupid': group_name}
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])
            return True

        raise HTTPResponseError(res)

    def get_user_groups(self, user_name):
        """Get a list of groups associated to a user.

        :param user_name:  name of user to list groups
        :returns: list of groups
        :raises: HTTPResponseError in case an HTTP error status was returned

        """

        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_CLOUD,
            'users/' + user_name + '/groups',
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])
            return [group.text for group in tree.find('data/groups')]

        raise HTTPResponseError(res)

    def user_is_in_group(self, user_name, group_name):
        """Checks if a user is in a group

        :param user_name:  name of user
        :param group_name:  name of group
        :returns: True if user is in group
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        return group_name in self.get_user_groups(user_name)

    def get_user(self, user_name):
        """Retrieves information about a user

        :param user_name:  name of user to query

        :returns: Dictionary of information about user
        :raises: ResponseError in case an HTTP error status was returned
        """
        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_CLOUD,
            'users/' + parse.quote(user_name),
            data={}
        )

        tree = ET.fromstring(res.content)
        self._check_ocs_status(tree)
        # <ocs><meta><statuscode>100</statuscode><status>ok</status></meta>
        # <data>
        # <email>frank@example.org</email><quota>0</quota><enabled>true</enabled>
        # </data>
        # </ocs>

        data_element = tree.find('data')
        return self._xml_to_dict(data_element)

    def remove_user_from_group(self, user_name, group_name):
        """Removes a user from a group.

        :param user_name:  name of user to be removed
        :param group_name:  name of group user is to be removed from
        :returns: True if user removed
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'DELETE',
            self.OCS_SERVICE_CLOUD,
            'users/' + user_name + '/groups',
            data={'groupid': group_name}
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])
            return True

        raise HTTPResponseError(res)

    def add_user_to_subadmin_group(self, user_name, group_name):
        """Adds a user to a subadmin group.

        :param user_name:  name of user to be added to subadmin group
        :param group_name:  name of subadmin group
        :returns: True if user added
        :raises: HTTPResponseError in case an HTTP error status was returned

        """

        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_CLOUD,
            'users/' + user_name + '/subadmins',
            data={'groupid': group_name}
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100, 103])
            return True

        raise HTTPResponseError(res)

    def get_user_subadmin_groups(self, user_name):
        """Get a list of subadmin groups associated to a user.

        :param user_name:  name of user
        :returns: list of subadmin groups
        :raises: HTTPResponseError in case an HTTP error status was returned

        """

        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_CLOUD,
            'users/' + user_name + '/subadmins',
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])

            groups = tree.find('data')

            return groups

        raise HTTPResponseError(res)

    def user_is_in_subadmin_group(self, user_name, group_name):
        """Checks if a user is in a subadmin group

        :param user_name:  name of user
        :param group_name:  name of subadmin group
        :returns: True if user is in subadmin group
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        return group_name in self.get_user_subadmin_groups(user_name)

    def share_file_with_user(self, path, user, **kwargs):
        """Shares a remote file with specified user

        :param path: path to the remote file to share
        :param user: name of the user whom we want to share a file/folder
        :param perms (optional): permissions of the shared object
            defaults to read only (1)
            http://doc.owncloud.org/server/6.0/admin_manual/sharing_api/index.html
        :param remote_user (optional): True if it is a federated users
            defaults to False if it is a local user
        :returns: instance of :class:`ShareInfo` with the share info
            or False if the operation failed
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        remote_user = kwargs.get('remote_user', False)
        perms = kwargs.get('perms', self.OCS_PERMISSION_READ)
        if (((not isinstance(perms, int)) or (perms > self.OCS_PERMISSION_ALL))
                or ((not isinstance(user, six.string_types)) or (user == ''))):
            return False

        if remote_user and (not user.endswith('/')):
            user = user + '/'
        path = self._normalize_path(path)
        post_data = {
            'shareType': self.OCS_SHARE_TYPE_REMOTE if remote_user else
            self.OCS_SHARE_TYPE_USER,
            'shareWith': user,
            'path': self._encode_string(path),
            'permissions': perms
        }

        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_SHARE,
            'shares',
            data=post_data
        )

        if self._debug:
            LOGGER.debug('OCS share_file request for file %s with permissions %i '
                  'returned: %i' % (path, perms, res.status_code))
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            data_el = tree.find('data')
            return ShareInfo(
                                {
                                    'id': data_el.find('id').text,
                                    'path': path,
                                    'permissions': perms
                                }
            )
        raise HTTPResponseError(res)

    def create_group(self, group_name):
        """Create a new group via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :param group_name:  name of group to be created
        :returns: True if group created
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_CLOUD,
            'groups',
            data={'groupid': group_name}
        )

        # We get 200 when the group was just created.
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])
            return True

        raise HTTPResponseError(res)

    def delete_group(self, group_name):
        """Delete a group via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :param group_name:  name of group to be deleted
        :returns: True if group deleted
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'DELETE',
            self.OCS_SERVICE_CLOUD,
            'groups/' + group_name
        )

        # We get 200 when the group was just deleted.
        if res.status_code == 200:
            return True

        raise HTTPResponseError(res)

    def get_groups(self):
        """Get groups via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :returns: list of groups
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_CLOUD,
            'groups'
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            groups = [x.text for x in tree.findall('data/groups/element')]

            return groups

        raise HTTPResponseError(res)

    def get_group_members(self, group_name):
        """Get group members via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :param group_name:  name of group to list members
        :returns: list of group members
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_CLOUD,
            'groups/' + group_name
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, [100])
            return [group.text for group in tree.find('data/users')]

        raise HTTPResponseError(res)

    def group_exists(self, group_name):
        """Checks a group via provisioning API.
        If you get back an error 999, then the provisioning API is not enabled.

        :param group_name:  name of group to be checked
        :returns: True if group exists
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_CLOUD,
            'groups?search=' + group_name
        )

        if res.status_code == 200:
            tree = ET.fromstring(res.content)

            for code_el in tree.findall('data/groups/element'):
                if code_el is not None and code_el.text == group_name:
                    return True

            return False

        raise HTTPResponseError(res)

    def share_file_with_group(self, path, group, **kwargs):
        """Shares a remote file with specified group

        :param path: path to the remote file to share
        :param group: name of the group with which we want to share a file/folder
        :param perms (optional): permissions of the shared object
            defaults to read only (1)
            http://doc.owncloud.org/server/6.0/admin_manual/sharing_api/index.html
        :returns: instance of :class:`ShareInfo` with the share info
            or False if the operation failed
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        perms = kwargs.get('perms', self.OCS_PERMISSION_READ)
        if (((not isinstance(perms, int)) or (perms > self.OCS_PERMISSION_ALL))
                or ((not isinstance(group, six.string_types)) or (group == ''))):
            return False

        path = self._normalize_path(path)
        post_data = {'shareType': self.OCS_SHARE_TYPE_GROUP,
                     'shareWith': group,
                     'path': path,
                     'permissions': perms}

        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_SHARE,
            'shares',
            data=post_data
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            data_el = tree.find('data')
            return ShareInfo(
                                {
                                    'id': data_el.find('id').text,
                                    'path': path,
                                    'permissions': perms
                                }
            )
        raise HTTPResponseError(res)

    def get_config(self):
        """Returns ownCloud config information
        :returns: array of tuples (key, value) for each information
            e.g. [('version', '1.7'), ('website', 'ownCloud'), ('host', 'cloud.example.com'),
            ('contact', ''), ('ssl', 'false')]
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        path = 'config'
        res = self._make_ocs_request(
            'GET',
            '',
            path
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            values = []

            element = tree.find('data')
            if element is not None:
                keys = ['version', 'website', 'host', 'contact', 'ssl']
                for key in keys:
                    text = element.find(key).text or ''
                    values.append(text)
                return zip(keys, values)
            else:
                return None
        raise HTTPResponseError(res)

    def get_attribute(self, app=None, key=None):
        """Returns an application attribute

        :param app: application id
        :param key: attribute key or None to retrieve all values for the
            given application
        :returns: attribute value if key was specified, or an array of tuples
            (key, value) for each attribute
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        path = 'getattribute'
        if app is not None:
            path += '/' + parse.quote(app, '')
            if key is not None:
                path += '/' + parse.quote(self._encode_string(key), '')
        res = self._make_ocs_request(
            'GET',
            self.OCS_SERVICE_PRIVATEDATA,
            path
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            values = []
            for element in tree.find('data').iter('element'):
                app_text = element.find('app').text
                key_text = element.find('key').text
                value_text = element.find('value').text or ''
                if key is None:
                    if app is None:
                        values.append((app_text, key_text, value_text))
                    else:
                        values.append((key_text, value_text))
                else:
                    return value_text

            if len(values) == 0 and key is not None:
                return None
            return values
        raise HTTPResponseError(res)

    def set_attribute(self, app, key, value):
        """Sets an application attribute

        :param app: application id
        :param key: key of the attribute to set
        :param value: value to set
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        path = 'setattribute/' + parse.quote(app, '') + '/' + parse.quote(
            self._encode_string(key), '')
        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_PRIVATEDATA,
            path,
            data={'value': self._encode_string(value)}
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            return True
        raise HTTPResponseError(res)

    def delete_attribute(self, app, key):
        """Deletes an application attribute

        :param app: application id
        :param key: key of the attribute to delete
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        path = 'deleteattribute/' + parse.quote(app, '') + '/' + parse.quote(
            self._encode_string(key), '')
        res = self._make_ocs_request(
            'POST',
            self.OCS_SERVICE_PRIVATEDATA,
            path
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)
            return True
        raise HTTPResponseError(res)

    def get_apps(self):
        """ List all enabled apps through the provisioning api.

        :returns: a dict of apps, with values True/False, representing the enabled state.
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        ena_apps = {}

        res = self._make_ocs_request('GET', self.OCS_SERVICE_CLOUD, 'apps')
        if res.status_code != 200:
            raise HTTPResponseError(res)
        tree = ET.fromstring(res.content)
        self._check_ocs_status(tree)
        # <data><apps><element>files</element><element>activity</element> ...
        for el in tree.findall('data/apps/element'):
            ena_apps[el.text] = False

        res = self._make_ocs_request('GET', self.OCS_SERVICE_CLOUD,
                                     'apps?filter=enabled')
        if res.status_code != 200:
            raise HTTPResponseError(res)
        tree = ET.fromstring(res.content)
        self._check_ocs_status(tree)
        for el in tree.findall('data/apps/element'):
            ena_apps[el.text] = True

        return ena_apps

    def get_version(self):
        """Gets the ownCloud version of the connected server

        :returns: ownCloud version as string
        """
        if self._version is None:
            self._update_capabilities()
        return self._version

    def get_capabilities(self):
        """Gets the ownCloud app capabilities

        :returns: capabilities dictionary that maps from
        app name to another dictionary containing the capabilities
        """
        if self._capabilities is None:
            self._update_capabilities()
        return self._capabilities

    def enable_app(self, appname):
        """Enable an app through provisioning_api

        :param appname:  Name of app to be enabled
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request('POST', self.OCS_SERVICE_CLOUD,
                                     'apps/' + appname)
        if res.status_code == 200:
            return True

        raise HTTPResponseError(res)

    def disable_app(self, appname):
        """Disable an app through provisioning_api

        :param appname:  Name of app to be disabled
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned

        """
        res = self._make_ocs_request('DELETE', self.OCS_SERVICE_CLOUD,
                                     'apps/' + appname)
        if res.status_code == 200:
            return True

        raise HTTPResponseError(res)

    @staticmethod
    def _normalize_path(path):
        """Makes sure the path starts with a "/"
        """
        if isinstance(path, FileInfo):
            path = path.path
        if len(path) == 0:
            return '/'
        if not path.startswith('/'):
            path = '/' + path
        return path

    @staticmethod
    def _encode_string(s):
        """Encodes a unicode instance to utf-8. If a str is passed it will
        simply be returned

        :param s: str or unicode to encode
        :returns: encoded output as str
        """
        if six.PY2 and isinstance(s, unicode):  # noqa: F821
            return s.encode('utf-8')
        return s

    @staticmethod
    def _check_ocs_status(tree, accepted_codes=[100]):
        """Checks the status code of an OCS request

        :param tree: response parsed with elementtree
        :param accepted_codes: list of statuscodes we consider good. E.g. [100,102] can be used to accept a POST
               returning an 'already exists' condition
        :raises: HTTPResponseError if the http status is not 200, or OCSResponseError if the OCS status is not one of the accepted_codes.
        """
        code_el = tree.find('meta/statuscode')
        if code_el is not None and int(code_el.text) not in accepted_codes:
            r = requests.Response()
            msg_el = tree.find('meta/message')
            if msg_el is None:
                msg_el = tree  # fallback to the entire ocs response, if we find no message.
            r._content = ET.tostring(msg_el)
            r.status_code = int(code_el.text)
            raise OCSResponseError(r)

    def make_ocs_request(self, method, service, action, **kwargs):
        """Makes a OCS API request and analyses the response

        :param method: HTTP method
        :param service: service name
        :param action: action path
        :param \*\*kwargs: optional arguments that ``requests.Request.request`` accepts
        :returns :class:`requests.Response` instance
        """

        accepted_codes = kwargs.pop('accepted_codes', [100])

        res = self._make_ocs_request(method, service, action, **kwargs)
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree, accepted_codes=accepted_codes)
            return res

        raise OCSResponseError(res)

    def _make_ocs_request(self, method, service, action, **kwargs):
        """Makes a OCS API request

        :param method: HTTP method
        :param service: service name
        :param action: action path
        :param \*\*kwargs: optional arguments that ``requests.Request.request`` accepts
        :returns :class:`requests.Response` instance
        """
        slash = ''
        if service:
            slash = '/'
        path = self.OCS_BASEPATH + service + slash + action

        attributes = kwargs.copy()

        if 'headers' not in attributes:
            attributes['headers'] = {}

        attributes['headers']['OCS-APIREQUEST'] = 'true'

        if self._debug:
            LOGGER.debug('OCS request: %s %s %s' % (method, self.url + path,
                                             attributes))

        res = self._session.request(method, self.url + path, **attributes)
        return res

    def _make_dav_request(self, method, path, **kwargs):
        """Makes a WebDAV request

        :param method: HTTP method
        :param path: remote path of the targeted file
        :param \*\*kwargs: optional arguments that ``requests.Request.request`` accepts
        :returns array of :class:`FileInfo` if the response
        contains it, or True if the operation succeeded, False
        if it didn't
        """
        if self._debug:
            LOGGER.debug('DAV request: %s %s' % (method, path))
            if kwargs.get('headers'):
                LOGGER.debug('Headers: ', kwargs.get('headers'))

        path = self._normalize_path(path)
        res = self._session.request(
            method,
            self._webdav_url + parse.quote(self._encode_string(path)),
            **kwargs
        )
        if self._debug:
            LOGGER.debug('DAV status: %i' % res.status_code)
        if res.status_code in [200, 207]:
            return self._parse_dav_response(res)
        if res.status_code in [204, 201]:
            return True
        raise HTTPResponseError(res)

    def _parse_dav_response(self, res):
        """Parses the DAV responses from a multi-status response

        :param res: DAV response
        :returns array of :class:`FileInfo` or False if
        the operation did not succeed
        """
        if res.status_code == 207:
            tree = ET.fromstring(res.content)
            items = []
            for child in tree:
                items.append(self._parse_dav_element(child))
            return items
        return False

    def _parse_dav_element(self, dav_response):
        """Parses a single DAV element

        :param dav_response: DAV response
        :returns :class:`FileInfo`
        """
        href = parse.unquote(
            self._strip_dav_path(dav_response.find('{DAV:}href').text)
        )

        if six.PY2:
            href = href.decode('utf-8')

        file_type = 'file'
        if href[-1] == '/':
            file_type = 'dir'

        file_attrs = {}
        attrs = dav_response.find('{DAV:}propstat')
        attrs = attrs.find('{DAV:}prop')
        for attr in attrs:
            file_attrs[attr.tag] = attr.text

        return FileInfo(href, file_type, file_attrs)

    def _strip_dav_path(self, path):
        """Removes the leading "remote.php/webdav" path from the given path

        :param path: path containing the remote DAV path "remote.php/webdav"
        :returns: path stripped of the remote DAV path
        """
        if path.startswith(self._davpath):
            return path[len(self._davpath):]
        return path

    def _webdav_move_copy(self, remote_path_source, remote_path_target,
                           operation):
        """Copies or moves a remote file or directory

        :param remote_path_source: source file or folder to copy / move
        :param remote_path_target: target file to which to copy / move
        :param operation: MOVE or COPY

        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """

        if operation != "MOVE" and operation != "COPY":
            return False

        if remote_path_target[-1] == '/':
            remote_path_target += os.path.basename(remote_path_source)

        if not (remote_path_target[0] == '/'):
            remote_path_target = '/' + remote_path_target

        remote_path_source = self._normalize_path(remote_path_source)
        headers = {
            'Destination': self._webdav_url + parse.quote(
                self._encode_string(remote_path_target))
        }

        return self._make_dav_request(
            operation,
            remote_path_source,
            headers=headers
        )

    def _xml_to_dict(self, element):
        """
        Take an XML element, iterate over it and build a dict

        :param element: An xml.etree.ElementTree.Element, or a list of the same
        :returns: A dictionary
        """
        return_dict = {}
        for el in element:
            return_dict[el.tag] = None
            children = list(el)
            if children:
                return_dict[el.tag] = self._xml_to_dict(children)
            else:
                return_dict[el.tag] = el.text
        return return_dict

    def _get_shareinfo(self, data_el):
        """Simple helper which returns instance of ShareInfo class

        :param data_el: 'data' element extracted from _make_ocs_request
        :returns: instance of ShareInfo class
        """
        if (data_el is None) or not (isinstance(data_el, ET.Element)):
            return None
        return ShareInfo(self._xml_to_dict(data_el))

    def _update_capabilities(self):
        res = self._make_ocs_request(
                'GET',
                self.OCS_SERVICE_CLOUD,
                'capabilities'
                )
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            self._check_ocs_status(tree)

            data_el = tree.find('data')
            apps = {}
            for app_el in data_el.find('capabilities'):
                app_caps = {}
                for cap_el in app_el:
                    app_caps[cap_el.tag] = cap_el.text
                apps[app_el.tag] = app_caps

            self._capabilities = apps

            version_el = data_el.find('version/string')
            edition_el = data_el.find('version/edition')
            self._version = version_el.text
            if edition_el.text is not None:
                self._version += '-' + edition_el.text

            if 'dav' in apps and 'chunking' in apps['dav']:
                chunking_version = float(apps['dav']['chunking'])
                if self._dav_endpoint_version > chunking_version:
                    self._dav_endpoint_version = None

                if self._dav_endpoint_version is None and chunking_version >= 1.0:
                    self._dav_endpoint_version = 1
                else:
                    self._dav_endpoint_version = 0

            return self._capabilities
        raise HTTPResponseError(res)
