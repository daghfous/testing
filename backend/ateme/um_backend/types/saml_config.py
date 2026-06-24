"""

SamlConfig class
"""
import os
from typing import List

from .base import BASE_SCHEMA_PATH
from .idp_config import IdpConfig, IdpType
from .roles_mapper import (
    DirectRolesMapper,
    SimpleRolesMapper,
    RolesMapper,
    RolesMapperType
)


class SamlConfig(IdpConfig):
    """ class SamlConfig """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "idp_saml_config.yaml")

    @property
    def idp_type(self) -> str:
        """
        Getter for the 'idp_type' field
        :return: The value of the 'idp_type' field
        """
        return self._data.get("idp_type", IdpType.saml.name)

    @idp_type.setter
    def idp_type(self, value: str):
        """
        Setter for the 'idp_type' field
        :param value: The value to set for the 'idp_type' field
        """
        self._data["idp_type"] = value

    @property
    def entity_id(self) -> str:
        """

        entity_id getter
        :return:
        """
        return self._data.get("entity_id")

    @entity_id.setter
    def entity_id(self, entity_id: str):
        """

        entity_id setter
        :param entity_id:
        """
        self._data["entity_id"] = entity_id

    @property
    def single_sign_on_service(self) -> str:
        """

        single_sign_on_service getter
        :return:
        """
        return self._data["single_sign_on_service"]

    @single_sign_on_service.setter
    def single_sign_on_service(self, single_sign_on_service: str):
        """

        single_sign_on_service setter
        :param single_sign_on_service:
        """
        self._data["single_sign_on_service"] = single_sign_on_service

    @property
    def single_logout_service(self) -> str:
        """

        single_logout_service getter
        :return:
        """
        return self._data["single_logout_service"]

    @single_logout_service.setter
    def single_logout_service(self, single_logout_service: str):
        """

        single_logout_service setter
        :param single_logout_service:
        """
        self._data["single_logout_service"] = single_logout_service

    @property
    def cert_fingerprint(self) -> str:
        """

        cert_fingerprint getter
        :return:
        """
        return self._data["cert_fingerprint"]

    @cert_fingerprint.setter
    def cert_fingerprint(self, cert_fingerprint: str):
        """

        cert_fingerprint setter
        :param cert_fingerprint:
        """
        self._data["cert_fingerprint"] = cert_fingerprint

    @property
    def sign_authn_request(self) -> bool:
        """ sign_authn_request getter """
        return self._data.get("sign_authn_request", False)

    @sign_authn_request.setter
    def sign_authn_request(self, sign_authn_request: bool):
        """ sign_authn_request setter """
        self._data["sign_authn_request"] = sign_authn_request

    @property
    def sign_logout_request(self) -> bool:
        """ sign_logout_request getter """
        return self._data.get("sign_logout_request", False)

    @sign_logout_request.setter
    def sign_logout_request(self, sign_logout_request: bool):
        """ sign_logout_request setter """
        self._data["sign_logout_request"] = sign_logout_request

    @property
    def sp_public_cert(self) -> str:
        """

        sp_public_cert getter
        :return:
        """
        return self._data.get("sp_public_cert")

    @sp_public_cert.setter
    def sp_public_cert(self, sp_public_cert: str):
        """

        sp_public_cert setter
        :param sp_public_cert:
        """
        self._data["sp_public_cert"] = sp_public_cert

    @property
    def sp_private_cert(self) -> str:
        """

        sp_private_cert getter
        :return:
        """
        return self._data.get("sp_private_cert")

    @sp_private_cert.setter
    def sp_private_cert(self, sp_private_cert: str):
        """

        sp_private_cert setter
        :param sp_private_cert:
        """
        self._data["sp_private_cert"] = sp_private_cert

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
            List[RolesMapper]: List of RolesMapper on saml config
        """
        return self._data.get('mappers', [])

    @mappers.setter
    def mappers(self, mappers: List[dict]):
        """
        Mappers setters, will cast to the right mapper class.

        Args:
            List[dict]: List of RolesMapper to set
        """
        # TODO: have to be more robust when no type ?
        _type_klass = {
            RolesMapperType.direct.name: DirectRolesMapper,
            RolesMapperType.simple.name: SimpleRolesMapper,
        }
        self._data["mappers"] = [_type_klass[item["type"]].from_dict(item) for item in mappers]
