"""
Ldap module
"""
# pylint: disable=no-member
# The no member pylint rule is disabled because python-ldap uses dynamic members that
# pylint cannot infer.
import os
from dataclasses import dataclass

import ldap

from ateme.um_backend.loggers import LOG
from ateme.um_backend.types.ldap_config import LdapConfig

def configure_ldap(
        log_detail_level: int = 0,
        network_timeout: int = 10
) -> None:
    """
    Configure python-ldap global options for logging, TLS, and network timeout.

    Notes:
    - SSL_CERT_FILE environment variable is optional.
        If set, it takes priority for TLS verification.
    - In our distroless container, SSL_CERT_FILE is set.

    Args:
        log_detail_level (int): Debug detail level for python-ldap (0-255).
        network_timeout (int): Timeout in seconds for LDAP network operations.
    Returns: None
    """
    # Set debug level
    # Level 0 → no debug (quiet mode)
    # Level 1–254 → increasing verbosity
    # Level 255 → full trace (very verbose, good for deep debugging)
    ldap.set_option(ldap.OPT_DEBUG_LEVEL, log_detail_level)

    # Use SSL_CERT_FILE if set
    # The environment variable SSL_CERT_FILE (available in container)
    # can be used to explicitly specify the CA certificate bundle to trust for TLS connections.
    # This ensures python-ldap (which relies on the OpenLDAP C library) can verify the
    # server certificate even in minimal container environments.
    ssl_cert_file = os.getenv("SSL_CERT_FILE")
    if ssl_cert_file:
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, ssl_cert_file)

    # Set network timeout
    ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, network_timeout)

@dataclass
class LdapSearchResult:
    """
    Represents a single LDAP search result entry.

    Attributes:
        dn (str):
            The distinguished name (DN) of the LDAP entry.
        attributes (dict[str, list[str]]):
            A mapping of attribute names to lists of attribute values.
            Each key corresponds to an LDAP attribute (e.g. "cn", "mail", "uid"),
            and each value is a list of strings representing the decoded attribute values.
    """
    dn: str
    attributes: dict[str, list[str]]

class LdapClient:  # pylint: disable=too-few-public-methods
    """
    LdapClient class
    """

    def __init__(self, ldap_config: LdapConfig):
        self.ldap_config = ldap_config

    def bind(self, username: str, password: str, is_user_dn: bool = False) \
        -> ldap.ldapobject.SimpleLDAPObject:
        """
        Bind to the LDAP server and return the connection object

        Args:
            username (str): username to bind with
            password (str): password to bind with
            is_user_dn (bool): whether the username is a full DN, else
                username is build automatically using the domain
                ({username}@{self.ldap_config.domain})
        Returns:
            ldap.ldapobject.SimpleLDAPObject: ldap object connection
        """
        ldap_uri = f"{self.ldap_config.protocol}://{self.ldap_config.server}"

        conn = ldap.initialize(uri=ldap_uri) # Initialize connection
        conn.protocol_version = ldap.VERSION3 # Force LDAPv3
        conn.set_option(ldap.OPT_REFERRALS, 0) # Disable automatic referrals (security)

        user = username # Prepare user for binding
        if self.ldap_config.domain and self.ldap_config.domain not in user and not is_user_dn:
            user = f"{username}@{self.ldap_config.domain}"
        conn.simple_bind_s(who=user, cred=password)
        return conn

    def search(self,
               connection: ldap.ldapobject.SimpleLDAPObject,
               attributes: list[str] | None,
               search_base: str,
               search_filter: str) -> list[LdapSearchResult]:
        """
        Perform an LDAP search starting from the specified base DN.

        Args:
            connection (ldap.ldapobject.SimpleLDAPObject):
                Ldap object connection
            attributes (list[str] | None):
                List of attribute names to retrieve for each entry.
                If None, all attributes are returned.
            search_base (str):
                The base distinguished name (DN) from which to start the search.
            search_filter (str):
                The LDAP search filter.
        Returns:
            list[LdapSearchResult]:
                A list of `LdapSearchResult` objects, each containing:
                    - `dn` (str): the entry distinguished name
                    - `attributes` (dict): mapping of attribute names to lists of string values
        """
        LOG.debug("LDAP Client performing LDAP search with search_base: %s, "
                  "search_filter: %s, attributes: %s",
                  search_base, search_filter, attributes)

        if not search_base or not search_filter:
            # If search_base or search_filter is None or empty, connection.search will raise an error
            LOG.warning(
                "LDAP search aborted: missing search_base or search_filter."
            )
            return []

        results = connection.search_s(
            base=search_base,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=search_filter,
            attrlist=attributes
        )
        if not results:
            LOG.warning("LDAP search returned no results.")
            return []

        # Convert results tuples (dn, attrs) → list of dicts
        # dn → is the Distinguished Name (a str) of the LDAP entry
        # attrs → is a dictionary of attributes for that entry
        # Each key is an attribute name (str), and each value is a
        # list of raw bytes (the raw LDAP attribute values)
        formatted: list[LdapSearchResult] = []
        for dn, attrs in results:
            if dn is None:
                continue
            # The LDAP protocol 'usually' transmits attribute values as binary data
            # Textual attributes like cn or mail are raw bytes
            # that's why we need to decode them
            # However, not always, that's why the following check.
            formatted.append(
                LdapSearchResult(
                    dn=dn,
                    attributes={
                        attr: [
                            v.decode('utf-8', 'ignore') if isinstance(v, bytes) else v
                            for v in values
                        ]
                        for attr, values in attrs.items()
                    }
                )
            )
        LOG.debug("LDAP search successful. Entries found: %d", len(formatted))
        return formatted
