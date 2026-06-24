"""

LdapConfig class
"""
import os

from ateme.um_backend.types.base import Base, BASE_SCHEMA_PATH
from ateme.um_backend.types.ldap_tls_config import LdapTlsConfig


class LdapConfig(Base):
    """ class LdapConfig """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "ldap_config.yaml")
    KEY_OBJECTS = {'tls_config': LdapTlsConfig.from_dict}

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
        return self._data.get("automatically_add_user", False)

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


    def __eq__(self, other):
        if not isinstance(other, LdapConfig):
            return NotImplemented
        return self.domain == other.domain and self.server == other.server and self.search == other.search \
            and self.group == other.group and self.use_ssl == other.use_ssl
