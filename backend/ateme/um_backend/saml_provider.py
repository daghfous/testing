"""Saml Provider
"""
import os
from enum import Enum
from typing import Tuple, Union, Dict

from onelogin.saml2 import compat
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.logout_response import OneLogin_Saml2_Logout_Response
from onelogin.saml2.response import OneLogin_Saml2_Response
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from onelogin.saml2.xml_utils import OneLogin_Saml2_XML

from ateme.um_backend.identity_provider import IdentityProvider
from .types.saml_config import SamlConfig

from .loggers import LOG


class IdpCallbackMode(Enum):
    """ IdpCallbackMode """
    LOGIN = 'login'
    LOGOUT = 'logout'


class UnknownModeException(Exception):
    """
    Raised when the callback mode of an IDP response could not be determined.
    It means that the response is invalid.
    """


class SamlProvider(IdentityProvider):
    """
    Saml Provider class
    """
    @staticmethod
    def get_callback_urls(relay_state: str, idp_name: str) -> Tuple[str, str, str]:
        """
        Generate and return assertion consumer service, single logout and entity id urls

        Args:
            relay_state (str): Relay state url
            idp_name (str): Idp name

        Returns:
            Tuple[str, str, str]: urls
        """
        acs = slo = os.path.join(relay_state, "users", "saml", f"callback/{idp_name}")
        entity_id = os.path.join(relay_state, "users", f"idp_metadata/{idp_name}")
        return acs, slo, entity_id

    def generate_auth_url(self, idp_config: SamlConfig, relay_state: str,
                          saml_session: dict = None, deploying_with_pmf: bool = False) -> Tuple[str, str]:
        """
        Generate single sign on and single logout idp urls

        Args:
            idp_config (SamlConfig): IDP config
            relay_state (str): Relay state url
            saml_session (dict, optional): Session SAML. Defaults to None.
            deploying_with_pmf (bool, optional): Bool set to True if user management is deployed in a PMF environment

        Returns:
            Tuple[str, str]: sso_url, slo_url
        """
        acs, slo, entity_id = self.get_callback_urls(relay_state, idp_config.idp_name)
        settings = self.get_saml_settings(idp_config, acs, slo, entity_id)
        saml_auth = OneLogin_Saml2_Auth({}, settings)
        redirect_url = os.path.join(relay_state, "#")
        if deploying_with_pmf:
            redirect_url = os.path.join(relay_state, "user-management")
        sso_url = saml_auth.login(redirect_url)
        slo_url = None
        if saml_session:
            slo_url = saml_auth.logout(redirect_url,
                                       name_id=saml_session['nameidentifier'],
                                       session_index=saml_session['session_index'])
        return sso_url, slo_url

    @staticmethod
    def get_saml_settings(idp_config: SamlConfig, sp_acs: str = "https://0.0.0.0/?acs",
                          sp_slo: str = "https://0.0.0.0/?sls",
                          entity_id: str = "https://0.0.0.0/metadata") -> OneLogin_Saml2_Settings:
        """
        Generate SAML Settings

        Args:
            idp_config (SamlConfig): Saml config
            sp_acs (str): Service provider acs url
            sp_slo (str): Service provider slo url
            entity_id (str): SP entity id

        Returns:
            OneLogin_Saml2_Settings: SAML Settings
        """

        data: dict = {
            "strict": False,
            "security": {
                "authnRequestsSigned": idp_config.sign_authn_request,
                "logoutRequestSigned": idp_config.sign_logout_request
            },
            "sp": {
                "entityId": f"{entity_id}",
                "assertionConsumerService": {
                    "url": f"{sp_acs}"
                },
                "singleLogoutService": {
                    "url": f"{sp_slo}"
                }
            },
            "idp": {
                "entityId": idp_config.entity_id,
                "singleSignOnService": {
                    "url": idp_config.single_sign_on_service
                },
                "singleLogoutService": {
                    "url": idp_config.single_logout_service
                },
                "x509cert": idp_config.cert_fingerprint
            }
        }

        if idp_config.sp_public_cert and idp_config.sp_private_cert:
            data['sp']['x509cert'] = idp_config.sp_public_cert
            data['sp']['privateKey'] = idp_config.sp_private_cert

        return OneLogin_Saml2_Settings(data)

    def compute_saml_response(self, idp_config: SamlConfig, response: str, relay_state: str,
                              mode: IdpCallbackMode) -> Union[OneLogin_Saml2_Response, OneLogin_Saml2_Logout_Response]:
        """
        Compute and returns a OneLogin_Saml2_Response instance

        Args:
            idp_config (SamlConfig): idp config
            response (str): encoded saml response
            relay_state (str): url where to redirect
            mode (str): mode login or logout

        Returns:
            OneLogin_Saml2_Response: OneLogin_Saml2_Response instance
        """
        acs, slo, entity_id = self.get_callback_urls(relay_state, idp_config.idp_name)
        settings = self.get_saml_settings(idp_config, acs, slo, entity_id)
        if mode == IdpCallbackMode.LOGOUT:
            return OneLogin_Saml2_Logout_Response(settings, response)
        return OneLogin_Saml2_Response(settings, response)

    @staticmethod
    def get_mode(response: str) -> IdpCallbackMode:
        """
        Get mode (login / logout) of an IDP SAML response based on its content
        Args:
            response (str): the received SAML response

        Returns:
            IdpCallbackMode: the mode of the response

        Raises:
            UnknownModeException: if the mode could not be determined
        """
        _response = compat.to_string(OneLogin_Saml2_Utils.decode_base64_and_inflate(response, ignore_zip=True))
        document = OneLogin_Saml2_XML.to_etree(_response)
        if OneLogin_Saml2_XML.query(document, '/samlp:LogoutResponse/samlp:Status/samlp:StatusCode'):
            return IdpCallbackMode.LOGOUT
        if OneLogin_Saml2_XML.query(document, '/samlp:Response/samlp:Status/samlp:StatusCode'):
            return IdpCallbackMode.LOGIN
        raise UnknownModeException('unable to determine mode')

    def validate_idp_config(self, idp_config: Dict) -> bool:
        """
        Validates the Saml configuration.

        Parameters:
            idp_config: The configuration for the IDP.

        Returns:
            bool: True if the IDP configuration is valid, False otherwise.
        """
        idp_saml_config = SamlConfig.from_dict(idp_config)
        settings = SamlProvider.get_saml_settings(idp_saml_config)
        try:
            OneLogin_Saml2_Auth({}, settings)
        except Exception as error:
            LOG.error("Bad SAML settings provided %s", error)
            raise error

        return True
