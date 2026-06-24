"""

LdapConfig class
"""
import os
from typing import List

from .base import BASE_SCHEMA_PATH
from .idp_config import IdpConfig, IdpType
from .ldap_tls_config import LdapTlsConfig
from .roles_mapper import (
    SimpleRolesMapper,
    RolesMapper
)


class LdapConfig(IdpConfig):
    """ class LdapConfig """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "idp_ldap_config.yaml")
    KEY_OBJECTS = {'tls_config': LdapTlsConfig.from_dict}

    @property
    def idp_type(self) -> str:
        """
        Getter for the 'idp_type' field
        :return: The value of the 'idp_type' field
        """
        return self._data.get("idp_type", IdpType.ldap.name)

    @idp_type.setter
    def idp_type(self, value: str):
        """
        Setter for the 'idp_type' field
        :param value: The value to set for the 'idp_type' field
        """
        self._data["idp_type"] = value

    @property
    def domain(self) -> str:
        """

        domain getter
        :return:
        """
        return self._data.get("domain")

    @domain.setter
    def domain(self, domain: str):
        """

        domain setter
        :param domain:
        """
        self._data["domain"] = domain

    @property
    def server(self) -> str:
        """

        server getter
        :return:
        """
        return self._data["server"]

    @server.setter
    def server(self, server: str):
        """

        server setter
        :param server:
        """
        self._data["server"] = server

    @property
    def search(self) -> str:
        """

        search getter
        :return:
        """
        return self._data["search"]

    @search.setter
    def search(self, search: str):
        """

        search setter
        :param search:
        """
        self._data["search"] = search

    @property
    def group(self) -> str:
        """

        group getter
        :return:
        """
        return self._data["group"]

    @group.setter
    def group(self, group: str):
        """

        group setter
        :param group:
        """
        self._data["group"] = group

    @property
    def search_filter(self) -> str:
        """

        search_filter getter
        :return:
        """
        return self._data.get("search_filter", "(objectClass=person)")

    @search_filter.setter
    def search_filter(self, search_filter: str):
        """

        group setter
        :param search_filter:
        """
        self._data["search_filter"] = search_filter

    @property
    def use_ssl(self) -> bool:
        """

        use_ssl getter
        :return:
        """
        return self._data.get("use_ssl", True)

    @use_ssl.setter
    def use_ssl(self, use_ssl: bool):
        """

        use_ssl setter
        :param use_ssl:
        """
        self._data["use_ssl"] = use_ssl

    @property
    def tls_config(self) -> LdapTlsConfig:
        """

        tls_config getter
        :return:
        """
        return self._data.get("tls_config")

    @tls_config.setter
    def tls_config(self, tls_config: LdapTlsConfig):
        """

        tls_config setter
        :param tls_config:
        """
        self._data["tls_config"] = tls_config

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

    @property
    def bind_dn(self) -> str | None:
        """bind_dn getter"""
        return self._data.get("bind_dn")

    @bind_dn.setter
    def bind_dn(self, bind_dn: str):
        """

        bind_dn setter
        :param bind_dn:
        """
        self._data["bind_dn"] = bind_dn

    @property
    def bind_password(self) -> str:
        """bind_password getter"""
        return self._data.get("bind_password")

    @bind_password.setter
    def bind_password(self, bind_password: str):
        """

        bind_password setter
        :param bind_password:
        """
        self._data["bind_password"] = bind_password

    @property
    def deny_access(self) -> bool:
        """

        Deny access property, usefull to know the default behavior
        on login and no mapper match.

        Returns:
            bool: Deny access
        """
        return self._data.get("deny_access", True)

    @deny_access.setter
    def deny_access(self, deny_access: bool):
        """

        Set default behavior when no mappers match.

        Args:
            deny_access (bool): Deny access boolean
        """
        self._data["deny_access"] = deny_access

    @property
    def mappers(self) -> List[RolesMapper]:
        """
        Mappers getters

        Returns:
            List[RolesMapper]: List of RolesMapper on ldap config
        """
        return self._data.get('mappers', [])

    @mappers.setter
    def mappers(self, mappers: List[dict]):
        """
        Mappers setters

        Args:
            List[dict]: List of RolesMapper to set
        """
        self._data["mappers"] = [SimpleRolesMapper.from_dict(item) for item in mappers]

    @property
    def user_filter(self) -> str:
        """

        user_filter getter
        :return:
        """
        return self._data.get("user_filter")

    @user_filter.setter
    def user_filter(self, user_filter: str):
        """

        user_filter setter
        :param user_filter:
        """
        self._data["user_filter"] = user_filter

    @property
    def protocol(self):
        """
        Property to return the protocol depending on the
        use_ssl.
        Returns:
            "ldaps" if use_ssl, otherwise "ldap
        """
        return "ldaps" if self.use_ssl else "ldap"

    def to_dict(self, with_bind_password: bool = False):
        """
        Returns a dict containing ldap config data

        Args:
            with_bind_password (bool, optional): Replace value by '' if True. Defaults to False.
        """
        data = super().to_dict()
        if not with_bind_password and self.bind_password:
            # Replace by an empty string to give the information to the frontend that the field has been filled
            data['bind_password'] = ''
        if not 'deny_access' in data:
            # Set default value
            data['deny_access'] = self.deny_access
        return data

    def __eq__(self, other):
        if not isinstance(other, LdapConfig):
            return NotImplemented
        return self.domain == other.domain and self.server == other.server and self.search == other.search \
            and self.group == other.group and self.use_ssl == other.use_ssl
