"""Ldap Provider
"""
import asyncio

from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
from ldap.filter import escape_filter_chars

from ateme.um_backend.identity_provider import IdentityProvider
from ateme.um_backend.ldap import LdapClient
from .types.ldap_config import LdapConfig
from . import Database
from .loggers import LOG

def build_user_search_filter(user_filter: str, username: str) -> str:
    """
    Safely build an LDAP search filter using escaped values to avoid LDAP injection.
    Args:
        user_filter : str
            The LDAP attribute used to identify the user (for example "uid" or
            "sAMAccountName"). This value will be safely escaped.
        username : str
            The username value to filter on. This value will also be safely escaped.

    Returns:
        str:
            A fully escaped LDAP search filter of the form "(attribute=value)".
    """
    safe_filter = escape_filter_chars(user_filter)
    safe_username = escape_filter_chars(username)
    return f"({safe_filter}={safe_username})"

class LdapProvider(IdentityProvider):
    """
    Ldap Provider class
    """

    def __init__(self,
                 db: Database,
                 executor: ThreadPoolExecutor):
        super().__init__(db)
        self._executor = executor

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def bind(self,
                   idp_name: str,
                   username: str,
                   password: str,
                   is_user_dn: bool,
                   loop: asyncio.AbstractEventLoop) -> bool:
        """
        Logs in the user with the given idp_name, username, and password.

        Args:
            idp_name (str): The name of the identity provider.
            username (str): The username of the user.
            password (str): The password of the user.
            is_user_dn (bool): True if we user user bind dn, otherwise False.
            loop: Asyncio event loop.
        """
        # Get idp from db
        idp_config = await self.db.get_idp_config_by_name(idp_name)
        if not idp_config:
            raise Exception(f"Idp {idp_name} not found")

        # Connect to ldap server
        ldap_client = LdapClient(idp_config)
        await loop.run_in_executor(self._executor,
                                   ldap_client.bind,
                                   username,
                                   password,
                                   is_user_dn)

    # pylint: disable=too-many-locals,too-many-branches
    async def retrieve_scopes(self,
                              idp_config: LdapConfig,
                              username: str,
                              password: str,
                              loop: asyncio.AbstractEventLoop) -> List[str]:
        # pylint: disable=too-many-locals, too-many-branches
        """
        Retrieve scopes corresponding to ldap user group mapping

        Args:
            idp_config (LdapConfig): Ldap config object.
            username (str): User name.
            password (str): User password.
            loop: Asyncio event loop.

        Returns:
            List (List[Scope], List[dict], List[str]): List of suser copes
        """
        requested_scopes: list[dict[str, list[str]]] = []
        mapper_names: set[str] = set()

        # Retrieve mapper names and values
        for mapper in idp_config.mappers:
            mapper_names |= {attribute.name.lower() for attribute in mapper.attributes}
            requested_scopes += [{attribute.value: mapper.scopes_to_add} for attribute in mapper.attributes]

        ldap_client = LdapClient(idp_config)
        is_bind_dn: bool = False

        # Compute credentials: user creds if bind_dn is not provided
        bind_dn, bind_password = username, password
        if idp_config.bind_dn and idp_config.bind_password:
            bind_dn, bind_password = idp_config.bind_dn, idp_config.bind_password
            is_bind_dn = True

        # Process ldap bind
        LOG.debug("Try to bind ldap user %s on idp %s", bind_dn, idp_config.idp_name)
        connection = await loop.run_in_executor(
            self._executor,
            ldap_client.bind,
            # bind arguments
            bind_dn,
            bind_password,
            is_bind_dn
        )

        # This is to avoid possible injection of malicious code
        search_filter = build_user_search_filter(idp_config.user_filter,
                                                 username)

        # Process ldap search
        LOG.debug(
            "Perform ldap search with filter %s, search base %s and attributes %s on idp %s",
            search_filter,
            idp_config.search,
            mapper_names,
            idp_config.idp_name,
        )
        response = await loop.run_in_executor(
            self._executor,
            ldap_client.search,
            # search arguments
            connection,         # connection
            mapper_names,       # attributes
            idp_config.search,  # search_base
            search_filter       # search_filter
        )

        LOG.debug(
            "Result of ldap search with filter %s and search base %s on idp %s: %s",
            search_filter,
            idp_config.search,
            idp_config.idp_name,
            response
        )
        if not response:
            return []

        # Append every user attributes in one list
        user_attributes = []
        for entry in response:
            attributes = entry.attributes
            for attr_name, attr_value in attributes.items():
                if attr_name.lower() in mapper_names:
                    user_attributes.extend(attr_value)

        # Filter requested scopes thanks to ldap search response
        scopes = []
        for scope_to_add in requested_scopes:
            for value, requested_scope in scope_to_add.items():
                if value in user_attributes:
                    LOG.debug(
                        "Role mapping matching on idp %s, scope %s added to user %s",
                        idp_config.idp_name,
                        requested_scope,
                        username
                    )
                    scopes += requested_scope

        # If no scopes retrieve
        if not scopes:
            scopes = idp_config.scopes
            if idp_config.deny_access:
                scopes = []

        return scopes

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def validate_idp_config(self,
                                  username: str,
                                  password: str,
                                  idp_config: Dict,
                                  is_user_dn: bool,
                                  loop: asyncio.AbstractEventLoop) -> bool:
        """
        Validates the Ldap configuration by attempting to authenticate with the given username and password.

        Parameters:
            username (str): The username for authentication.
            password (str): The password for authentication.
            idp_config: The configuration for the IDP.
            is_user_dn (bool): True if we user user bind dn, otherwise False.
            loop: Asyncio event loop.

        Returns:
            bool: True if the IDP configuration is valid, False otherwise.
        """
        idp_ldap_config = LdapConfig.from_dict(idp_config)
        ldap_client = LdapClient(idp_ldap_config)
        LOG.debug("Bind with username %s (is_user_dn %s) on idp '%s'",
                 username, is_user_dn, idp_ldap_config.idp_name)
        try:
            connection = await loop.run_in_executor(
                self._executor,
                ldap_client.bind,
                username,
                password,
                is_user_dn
            )
        except Exception as exception:
            LOG.error(
                "LDAP Bind Exception on idp %s for username %s: %s",
                idp_ldap_config.idp_name,
                username,
                exception
            )
            raise exception

        if idp_ldap_config.search is None or idp_ldap_config.user_filter is None or not idp_ldap_config.search_filter:
            LOG.warning(
                "Search base_dn or user filter not defined for idp %s, skipping search",
                idp_ldap_config.idp_name
            )
            return True
        try:
            LOG.debug("Search request with user_filter '%s' from base_dn '%s' on idp '%s'",
                     idp_ldap_config.user_filter,
                     idp_ldap_config.search,
                     idp_ldap_config.idp_name)
            search_response = await loop.run_in_executor(
                self._executor,
                ldap_client.search,
                connection,
                [idp_ldap_config.user_filter],
                idp_ldap_config.search,
                idp_ldap_config.search_filter
            )
            LOG.debug("search_response for idp %s: %d entries", idp_ldap_config.idp_name, len(search_response)
                      if search_response else 0)
        except Exception as exception:
            LOG.error("LDAP Search Exception with user_filter '%s' from base_dn '%s' on idp '%s': %s",
                      idp_ldap_config.user_filter,
                      idp_ldap_config.search,
                      idp_ldap_config.idp_name,
                      exception)
            raise exception
        return True
