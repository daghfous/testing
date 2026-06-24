"""

IdpConfig class
"""

from enum import Enum, auto

from ateme.um_backend.types.base import Base


class IdpType(Enum):
    """
    class IdpType
    """
    # pylint: disable=invalid-name
    default = auto()
    local = auto()
    ldap = auto()
    saml = auto()


class IdpConfig(Base):
    """ class IdpConfig """

    @property
    def idp_name(self) -> str:
        """

        name getter
        :return:
        """
        return self._data.get("idp_name", "")

    @idp_name.setter
    def idp_name(self, idp_name: str):
        """

        domain setter
        :param idp_name:
        """
        self._data["idp_name"] = idp_name

    @property
    def idp_label(self) -> str:
        """

        name getter
        :return:
        """
        return self._data.get("idp_label", "")

    @idp_label.setter
    def idp_label(self, idp_label: str):
        """

        domain setter
        :param idp_label:
        """
        self._data["idp_label"] = idp_label

    @property
    def idp_type(self) -> str:
        """
        Getter for the 'idp_type' field
        :return: The value of the 'idp_type' field
        """
        return self._data.get("idp_type", IdpType.default.name)

    @idp_type.setter
    def idp_type(self, value: str):
        """
        Setter for the 'idp_type' field
        :param value: The value to set for the 'idp_type' field
        """
        self._data["idp_type"] = value

    @property
    def automatically_add_user(self) -> bool:
        """

        automatically_add_user getter
        :return:
        """
        return self._data.get("automatically_add_user", True)

    @automatically_add_user.setter
    def automatically_add_user(self, automatically_add_user: bool):
        """

        automatically_add_user setter
        :param automatically_add_user:
        """
        self._data["automatically_add_user"] = automatically_add_user

    @property
    def scopes(self) -> list:
        """

        scopes getter
        :return:
        """
        return self._data.get("scopes", ["all:guest"])

    @scopes.setter
    def scopes(self, scopes: list):
        """

        scopes setter
        :param scopes:
        """
        self._data["scopes"] = scopes
