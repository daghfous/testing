"""
um_backend module
"""

from ateme.um_backend.database import Database
from ateme.um_backend.types import *  # pylint: disable=W0614
from ateme.um_backend.user_management import UserManagementApi
from ateme.um_backend.utils import (
    parse_scopes_and_actions,
    DEFAULT_API_DESCRIPTORS_KEY,
    DEFAULT_SCOPES_KEY,
    DEFAULT_ACTIONS_KEY
)

__all__ = [
    "Request",
    "RequestMethod",
    "Action",
    "Scope",
    "ScopeFilterMode",
    "ScopeFilter",
    "parse_scopes_and_actions",
    "Database",
    "User",
    "load_default_actions",
    "load_default_scopes",
    "LdapConfig",
    "LdapTlsConfig",
    "IdpType",
    "IdpConfig",
    "IdpLocalConfig",
    "DEFAULT_LOCAL_IDP_NAME",
    "Configuration",
    "PublicConfiguration",
    "PasswordPolicy",
    "ApiDescriptor",
    "DefaultScopes",
    "DEFAULT_API_DESCRIPTORS_KEY",
    "DEFAULT_SCOPES_KEY",
    "DEFAULT_ACTIONS_KEY",
    "UserManagementApi"
]
