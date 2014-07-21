import urllib
import ResponseError
import xml.etree.ElementTree as ET


class ExtendedAPI():
    """ExtendedAPI client"""

    def set_user_preference(self, userid, appid, configkey, configvalue):
        """Sets an user preference attribute

        :param userid: key of the preference to set
        :param appid: value to set
        :param configkey: value to set
        :param configvalue: value to set
        :returns: True if the operation succeeded, False otherwise
        :raises: ResponseError in case an HTTP error status was returned
        """
        path = 'userdata/' + urllib.quote(userid)
        res = self.__make_ocs_request(
            'PUT',
            'cloud',
            path,
            data={configkey: configvalue}
        )
        if res.status_code == 200:
            tree = ET.fromstring(res.text)
            self.__check_ocs_status(tree)
            return True
        raise ResponseError(res)

