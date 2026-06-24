"""

LdapTlsConfig class
"""
import os

from .base import Base, BASE_SCHEMA_PATH


class LdapTlsConfig(Base):
    """ class LdapConfig """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "ldap_tls_config.yaml")

    @property
    def certificate_file(self) -> str:
        """

        certificate_file getter
        :return:
        """
        return self._data.get("certificate_file")

    @certificate_file.setter
    def certificate_file(self, certificate_file: str):
        """

        certificate_file setter
        :param certificate_file:
        """
        self._data["certificate_file"] = certificate_file

    @property
    def private_key_file(self) -> str:
        """

        private_key_file getter
        :return:
        """
        return self._data.get("private_key_file")

    @private_key_file.setter
    def private_key_file(self, private_key_file: str):
        """

        private_key_file setter
        :param private_key_file:
        """
        self._data["private_key_file"] = private_key_file

    @property
    def ca_certs_file(self) -> str:
        """

        ca_certs_file getter
        :return:
        """
        return self._data.get("ca_certs_file")

    @ca_certs_file.setter
    def ca_certs_file(self, ca_certs_file: str):
        """

        ca_certs_file setter
        :param ca_certs_file:
        """
        self._data["ca_certs_file"] = ca_certs_file
